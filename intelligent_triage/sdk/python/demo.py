from SDK import FindDoctor

sdk = FindDoctor(clientId="mobimedical", orgId="test", name="J",
                 dob="2006-03-01", gender="female", card_no="1234",
                 wechatOpenId="123", apiUrl="http://docfinder.sparta.html5.qq.com")

res = sdk.create_session()
print(res)
res = sdk.find_doctor("恶心，呕吐")
print(res)
res = sdk.find_doctor("头晕")
print(res)
res = sdk.find_doctor("便血")
print(res)
