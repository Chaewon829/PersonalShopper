import pickle
import os
from tqdm import tqdm
from collections import Counter
from scraping import *
from openai import OpenAI
from session import *
from agent import *
import config


######################################### 쇼핑 검색어 input 받기 #########################################
#url scraping
keyword = input("Search KeyWord 입력:") #질기지 않은 1등급 무항생제 스테이크용 한우 안심을 사고 싶어.
n_top = int(input("검색 상위 N값 입력:"))


######################################### Keyword Agent #########################################
#keyword_agent
input_keyword = [] #scraper 가 사용할 키워드
decision_keyword = [] #decision agent가 사용할 키워드

#TODO : Option 키워드 분리하는 작업 
client = OpenAI(api_key= config.api_key)

#voting 구현
n_select = 1
n_sh_lst, n_dc_lst = KeywordAgentVoting(n_select, client, keyword)


#앙상블 중 가장 많이 나온 키워드만 추출
input_keyword.append(Counter(n_sh_lst).most_common(1)[0][0])
decision_keyword = list(set(n_dc_lst))

#decision_keyword에 여러 키워드가 존재하면 None 값 제외시키기
if len(decision_keyword) > 1:
  try:
    decision_keyword.remove('None')
  except:
    pass

print()
print(f"input_keyword:{input_keyword}")
print(f"decision_keyword:{decision_keyword}")
print()


######################################### Scarping 실행 #########################################
#분리된 키워드로 scraping 실행하기
print('scraping 작업 실행')

url_path = os.path.join("cache", "finalLink.pickle")

# func_arr = [NaverFinalUrl, KurlyLinkGet]
# fina_link_lst = []

#scraping 결과
final_link_lst, data_details, data_reviews = NaverFinalUrl(input_keyword[0],n_top)
with open(url_path, "wb") as fw_url:
    pickle.dump(final_link_lst, fw_url)
print("scraping 완료!!")
print()


######################################### Decision Agent 실행 #########################################
#decision_agent : use gpt api
#Step 1. select gpt 
input_strings = '\n'.join(list(str(i) for i in data_details))
prompt_text = '''
Among the products below, please return the product numbers that meet all the conditions of the user request according to the format.If there are multiple user requests, all conditions must be met.
For example, if product 3 and product 5 satisfy the conditions, print 3 5
If none of the products meet the conditions, please return empty string and nothing else.
'''
#TODO : 현재 상태 : 만약 아무 상품도 조건을 만족하지 않는다면 empty string return됨. -> 이때 어떤 방식을 취할지 결정하고, 코드 만들기 (사용자에게 알리거나, 필터를 줄여서 다시 필터링 시도하거나....)
prompt_text = prompt_text + f"user_request : {','.join(decision_keyword)}\n "
prompt_text +=  '\n'.join(list(str(i) for i in data_details))
# print(f"input_prompt = {prompt_text}")

response = client.chat.completions.create(
  model="gpt-4-turbo",
  messages=[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content":prompt_text},
    
  ],
  temperature = 0,
  max_tokens=50
)

result = response.choices[0].message.content
#TODO : GPT의 불확실성 때문에 번호가 아닌 다른 말이 포함된다면, 오류 control 하는 코드 (지피티한테 다시 번호만 주라고 시키거나, 시스템 오류로 종료 메시지 넣기)

#Step 2. compare gpt : 위의 select agent에서 선택된 number의 product들 중 가장 "좋은" 상품을 compare 하여 최종적으로 단 하나의 product의 url을 반환한다. 
select_numbers=list(map(int,result.split(' ')))
print(f"select_numbers = {select_numbers}")

prompt_text = "Compare the products below and choose one of the best products and Print out the selected product number and the reason for selecting the product according to the format  If there is only 1 product, choose that one product. Don't print out anything other than the number and reason. Please return the string that connects the number and reason with @. For example, if product 3 is selected, print 3@reason."


for idx, data in enumerate(data_reviews) :
    if (idx + 1) in select_numbers : 
        prompt_text += str(data)

response = client.chat.completions.create(
  model="gpt-4-turbo",
  messages=[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content":prompt_text},
    
  ],
  temperature =0,
  max_tokens=50
)

result = response.choices[0].message.content
result, reason = result.split('@')
print()
print(f"결정 이유 : {reason}")
print()
print(f"Final_Link_number:{result}번 링크")
print()
#TODO : gpt의 불확실성 때문에 하나의 숫자외에 다른게 output으로 나온다면, 오류 control 하는 코드

save_final_path = os.path.join("cache", "result_url.txt")
for idx, url in enumerate(final_link_lst) :
    if (idx + 1) == int(result) : 
        with open(save_final_path, "w") as file :
            file.write(url)


######################################### Back End #########################################
final_link = final_link_lst[int(result)-1]
print(f"최종 선택 사이트 URL: {final_link}")
print()
print('상기 사이트의 ID, PW를 입력해주세요')
login_id = config.naver_id
login_pw = config.naver_pw
# login_id = input("ID:")
# login_pw = input("PW:")
print()


NaverSession(login_id, login_pw, final_link)