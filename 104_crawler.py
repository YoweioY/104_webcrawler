#%%
#----------------------------爬蟲------------------------------
# 載入selenium相關模組
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time
# 設定chrome Diver 的執行路徑
options = Options()
options.chrome_executable_path = "C:\pythontraining\backup\chromedriver.exe"
# 建立 Driver 實體物件，用程式操作瀏覽器運作
driver = webdriver.Chrome(options = options)
# 連線到 104 工作搜尋網頁
url_104 = "https://www.104.com.tw/jobs/main/"
driver.get(url_104)
# 輸入搜尋條件，按下搜尋按鈕
inquiry_input = driver.find_element(By.ID, "ikeyword")
inquiry_input.send_keys("資料分析")
# 按下搜尋鍵
inquiry_input.send_keys(Keys.RETURN)

# 等待查詢完成
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
wait = WebDriverWait(driver, 10)  # 等待10秒
element = wait.until(EC.presence_of_element_located((By.ID, "js-job-content")))  # 等待"js-job-content"元素載入完成

# 建立空資料框
import pandas as pd
import numpy as np
df = pd.DataFrame(columns=['title', 'company', 'place', 'exeperience', 'education', 'wage', 'url'])

page = 0
n = 0
all_pages = 150
other_words = []
while True:

    # 找到每個搜索結果的元素列表
    titles = driver.find_elements(By.CLASS_NAME, "js-job-link") # 抓標題
    companies = driver.find_elements(By.CSS_SELECTOR, 'a[title*="公司名"]') # 抓公司名
    conditions = driver.find_elements(By.CSS_SELECTOR, 'article.job-list-item') # 抓地區、學經歷
    wages = driver.find_elements(By.CLASS_NAME,"b-tag--default") #抓薪資
    job_links = driver.find_elements(By.CLASS_NAME, "js-job-link") #結果網址

    for i in range(len(titles)):
        title = titles[i].text # 標題
        company = companies[i].text.strip() # 公司名
        cd_element = conditions[i].find_element(By.CSS_SELECTOR, 'ul.b-list-inline.b-clearfix.job-list-intro.b-content')
        cd = cd_element.text.strip()
        cd_columns = cd.split("\n") # 將地區、學經歷分開
        job_link = job_links[i].get_attribute("href") # 職缺網址
        df = df.append({'title': title, 
                        'company': company, 
                        'place': cd_columns[0], 
                        'exeperience': cd_columns[1], 
                        'education': cd_columns[2],
                        'url': job_link}, 
                    ignore_index=True)
    # 薪水
    for wage in wages:
        wage_words = wage.text.strip()
        wage_columns = wage_words.split("\n")
        if wage_columns[0] != "":
            words = wage_columns[0]
            if words[:2] in ["月薪", "年薪", "時薪", "待遇", "論件", "日薪"]:
                df.iloc[n, 5] = words
                n += 1
            else:
                other_words.append(words)
    next_page_button = driver.find_element(By.XPATH, '//button[contains(text(), "下一頁")]')
    if page == all_pages-1:
        break
    else: 
        next_page_button.click()
    time.sleep(5) #等待五秒鐘
    page += 1
print(page)

driver.close()

#%%
print(df.iloc[534,6])
print(df.iloc[1369,6])
# %%
#--------------------------資料處理--------------------------------
# 排除標題沒有關鍵字的資料
df_da = pd.DataFrame(columns=['title', 'company', 'place', 'exeperience', 'education', 'wage', 'url'])
for i in range(len(df)):
    if any(x in df.iloc[i,0] for x in ["數據","資料","Data","data","DATA","AI","人工智慧","系統分析","智慧製造","市場分析",
                                       "產業分析","商業分析","統計","Python","Power BI", "Tableau","SQL","機器學習","Machine Learning"]):
        df_da = df_da.append(df.iloc[i,:])

# 排除非台灣本島的資料
cities = ["台北市", "新北市", "桃園市", "新竹市", "新竹縣", "苗栗縣", "台中市", "彰化縣", "雲林縣", "嘉義縣", "嘉義市", "台南市", "高雄市", "屏東縣", "台東縣", "花蓮縣", "宜蘭縣", "基隆市"]
mask = df_da.iloc[:,2].str[:3].isin(cities)
df_taiwan = df_da[mask]
df_taiwan.reset_index(inplace=True,drop=True) # 重整index

# 把時薪與論件計酬的資料刪除
hours_list = []
for i in range(len(df_taiwan)):
    if df_taiwan.iloc[i,5][:2] == "時薪" or df_taiwan.iloc[i,5][:2] == "論件":
        hours_list.append(i)
df_taiwan.drop(index=hours_list, inplace=True) # 刪除時薪的資料
df_taiwan.reset_index(inplace=True,drop=True) # 重整index

# %%
# 將地區拆成縣市與區域兩欄
df_taiwan['place'] = df_taiwan['place'].apply(lambda x: x.ljust(4)) # 不滿四個字的填補成空格
df_new = pd.DataFrame({'county': df_taiwan['place'].str[:3], 'distinct': df_taiwan['place'].str[3:]}) # 將 place 列分割為兩列，分別為前三個字和三個字後
df_taiwan = pd.concat([df_taiwan, df_new], axis=1) # 合併
df_taiwan.drop('place', axis=1, inplace=True) # 刪除place
county = df_taiwan.pop('county') # 先將欄位取出，並將其從原本的位置9與10移除
distinct = df_taiwan.pop('distinct')
df_taiwan.insert(2, 'county', county) # 再將欄位插入到新的位置2,3
df_taiwan.insert(3, 'distinct', distinct)
df_taiwan = df_taiwan.replace(' ', np.nan) # 將空格改遺失值


#%%
# 將字串轉數值，年薪轉月薪
df_taiwan_num = df_taiwan.copy()
year_wages = {}
each_month = 14
days = 20
for i in range(len(df_taiwan_num)):
    if df_taiwan_num.iloc[i,6] != "待遇面議":
        # 月薪
        clean_words = df_taiwan_num.iloc[i,6].replace(",", "")
        if clean_words[:2]=="月薪" and clean_words[-1]=="元":
            clean_words = clean_words[2:-1]
            if "~" not in clean_words:
                df_taiwan_num.iloc[i,6] = int(clean_words)
            else:
                for j in range(len(clean_words)):                                                 
                    if clean_words[j] == "~":
                        front = int(clean_words[:j])
                        back = int(clean_words[j+1:]) 
                df_taiwan_num.iloc[i,6] = round((front+back)/2.0, 0)
        elif clean_words[:2]=="月薪" and clean_words[-1]=="上":
            df_taiwan_num.iloc[i,6] = int(clean_words[2:-3])
        # 年薪
        if clean_words[:2]=="年薪" and clean_words[-1]=="元":
            year_wages[df_taiwan_num.index[i]] = df_taiwan_num.iloc[i,6]
            clean_words = clean_words[2:-1]
            if "~" not in clean_words:
                df_taiwan_num.iloc[i,6] = round(int(clean_words)/each_month,0)
            else:
                for j in range(len(clean_words)):                                                 
                    if clean_words[j] == "~":
                        front = int(clean_words[:j])
                        back = int(clean_words[j+1:]) 
                df_taiwan_num.iloc[i,6] = round((front+back)/(2.0*each_month), 0)
        elif clean_words[:2]=="年薪" and clean_words[-1]=="上":
            year_wages[df_taiwan_num.index[i]] = df_taiwan_num.iloc[i,6]
            df_taiwan_num.iloc[i,6] = round(int(clean_words[2:-3])/each_month,0)
        # 日薪
        if clean_words[:2]=="日薪" and clean_words[-1]=="元":
            year_wages[df_taiwan_num.index[i]] = df_taiwan_num.iloc[i,6]
            clean_words = clean_words[2:-1]
            if "~" not in clean_words:
                df_taiwan_num.iloc[i,6] = round(int(clean_words)*days,0)
            else:
                for j in range(len(clean_words)):                                                 
                    if clean_words[j] == "~":
                        front = int(clean_words[:j])
                        back = int(clean_words[j+1:]) 
                df_taiwan_num.iloc[i,6] = round(((front+back)/2.0)*days, 0)
        elif clean_words[:2]=="日薪" and clean_words[-1]=="上":
            year_wages[df_taiwan_num.index[i]] = df_taiwan_num.iloc[i,6]
            df_taiwan_num.iloc[i,6] = round(int(clean_words[2:-3])*days,0)


# %%
df_taiwan_num.to_csv('0722_104job_DA.csv', encoding="big5", index=False, errors="ignore")
#%%
df.to_csv('0722_104job_raw.csv', encoding="big5", index=False, errors="ignore")
# %%
# 算不含待遇面議的薪資平均
total = 0
number = 0
for i in range(len(df_taiwan_num)):
    if df_taiwan_num.iloc[i,-2]!="待遇面議":
        total = total + df_taiwan_num.iloc[i,-2]
        number += 1
print(total/number)
# %%
