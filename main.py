from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
import requests
import re
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
import smtplib
from string import Template
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


#MAILSERVER
HOST = 'smtp.gmail.com'
PORT = 587

# BURAYA MAIL BİLGİLERİNİ YAZ
YOUR_EMAIL = ('GMAIL')
PASSWORD = ('PASSWORD')

path_to_pdf = ''

smtp = smtplib.SMTP(host=HOST,port=PORT)
smtp.connect(HOST,PORT)
smtp.starttls()
smtp.login(YOUR_EMAIL,PASSWORD)

#Chrome Options
chromeOptions = Options()
chromeOptions.add_argument("--start-maximized")
#chromeOptions.add_argument("--headless")
chromeOptions.add_argument("--no-sandbox")
chromeOptions.add_argument("--disable-dev-shm-usage")
chromeOptions.add_argument("--log-level=3")

#Install Driver
webdriverService = Service(ChromeDriverManager().install())
#Set up
driver = webdriver.Chrome(service=webdriverService,options= chromeOptions)

search_text = input("Enter a keyword to search")



def go_to_maps():
    driver.get("https://www.google.com/maps")
    searchBox = driver.find_element(By.ID, "searchboxinput")
    searchBox.send_keys(search_text)
    searchBox.send_keys(Keys.ENTER)
    time.sleep(5)
go_to_maps()

def scroll_and_load(driver, search_text):

    results_list = driver.find_element(By.XPATH, f"//div[@aria-label='{search_text} için sonuçlar']")

    last_height = driver.execute_script("return arguments[0].scrollHeight", results_list)
    
    while True:
        #scroll
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_list)
        time.sleep(2.5)
        new_height = driver.execute_script("return arguments[0].scrollHeight", results_list)
        if new_height == last_height:
            break
        last_height = new_height
    driver.execute_script("return arguments[0].scrollIntoView(true);", results_list)
scroll_and_load(driver,search_text)

pageSource = driver.page_source

soup = BeautifulSoup(pageSource,"html.parser")

def extract_email_from_website(website):
    try:
        response = requests.get(website, timeout=5)
        if response.status_code == 200:
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', response.text)
            return emails if emails else ["No email found"]
        else:
            return ["Failed to fetch website"]
    except RequestException:
        return ["Error accessing website"]

#because google sometimes changes classname's
possible_classes = [
    "Nv2PK tH5CWc THOPZb",
    "Nv2PK THOPZb CpccDe",
    "Nv2PK Q2HXcd THOPZb"
]
data_containers = None
for class_name in possible_classes:
    data_containers = soup.find_all("div", class_=class_name)
    if data_containers:
        print(f"Class found: {class_name}")
        break
if not data_containers:
    print("No matching data containers found. Check the class names or the page structure.")
results = []
def scrape_data():
    for container in data_containers:
        name = container.find("div", class_="qBF1Pd fontHeadlineSmall").text
        try:
            ratings = container.find("span",class_='MW4etd').text
        except AttributeError:
            ratings= "Has No rating"
        try:
            comments = container.find("span",class_ = "UY7F9").text
        except AttributeError:
            comments = "Has No comments."
        try:
            website = container.find("a",{"class":"lcr4fd S9kvJb"}).get("href")
        except AttributeError:
            website = "No Website"
        try:
            phoneNumber = container.find("span", class_="UsdlK").text
        except AttributeError:
            phoneNumber = "No phone number"
        if website != "No Website":
            emails = extract_email_from_website(website)
        else:
            emails = ["No website to extract email"]
        
        results.append({"name": name, "ratings": ratings, "comments" : comments,"website":website, "phone number": phoneNumber , "emails" : ", ".join(emails)})
#scrape that address
def scrape_address():
    data_container = driver.find_elements(By.CLASS_NAME , "hfpxzc")
    action = ActionChains(driver)
    processed_index = set()
#Sometimes it skips frames
    for index , container in enumerate(data_container):
        if index in processed_index:
            continue
        try:
            action.move_to_element(container).click().perform()
            action.move_to_element(container).click().perform()
            time.sleep(1.2)
            address = driver.find_element(By.XPATH, '//div[contains(@class, "Io6YTe") and contains(@class, "fontBodyMedium") and contains(@class, "kR99db") and contains(@class, "fdkmkc")]').text
            time.sleep(1.2)
            if index < len(results):
                results[index]["address"] = address
            #results.append({"address":address})
        except Exception as e:
            print("Hata" , e)
            time.sleep(1)        
        if (index + 1) % 3 == 0:
            try:
                driver.execute_script("arguments[0].scrollIntoView();", container)
                time.sleep(1.2)
            except Exception as e:
                print("Scroll Error:", e)

scrape_data()
time.sleep(5)
#scrape_address()


print("-"*50)

df = pd.DataFrame(results)
df.to_csv("google_maps_data.csv", index=False)

def get_message(filename):
    with open(filename,mode='r',encoding='utf-8') as message_file:
        message = message_file.read()
    return Template(message)


def get_mails():
    emails = []
    names = []
    dataframe = pd.read_csv('google_maps_data.csv')
    invalid_values = ["No email found", "Failed to fetch website","Error accessing website"]
    dataframe = dataframe[~dataframe["emails"].isin(invalid_values)]
    dataframe.drop_duplicates(subset='emails',keep='first',inplace=True)
    dataframe["emails"] = dataframe["emails"].str.split(", ")
    dataframe = dataframe.explode("emails")
    dataframe = dataframe.drop_duplicates(subset=["emails"])
    for index, row in dataframe.iterrows():
        if '@' in row['emails']:
            emails.append(row['emails'])
            names.append(row['name'])
    dataframe = dataframe[["name", "emails"]]
    dataframe.to_csv('CLEANLIST.csv',index=False)
    return emails ,names

emails, names = get_mails()
message_template = get_message('message.txt')

def main():
    for name,email in zip(names,emails):
        msg = MIMEMultipart()
        message = message_template.substitute(name=name)
        msg['From'] = YOUR_EMAIL
        msg['To'] = email
        msg['Subject'] = 'Erasmus+ staj programı başvurusu' #Mail konusu
        
        msg.attach(MIMEText(message,'plain'))
        try:
            with open(path_to_pdf, "rb") as f:
                #attach = email.mime.application.MIMEApplication(f.read(),_subtype="pdf")
                attach = MIMEApplication(f.read(),_subtype="pdf")
            attach.add_header('Content-Disposition','attachment',filename=str(path_to_pdf))
            msg.attach(attach)
        except:
            print('No such file in direction' , path_to_pdf)
        smtp.send_message(msg)
        
        del msg
    smtp.quit()

main()

