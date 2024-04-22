# auto_trading
auto_trading made using python
```shell
#필요한 패키지 download
pip3 install -r requirements.txt

#API KEY 입력
vim .env

#background 실행
nohup python3 -u autotrade.py > output.log 2>&1 &

#로그 확인
cat output.log
tail -f output.log

#pid 확인 
ps ax | grep autotrade.py

#process kill
kill -9 PID
ex. kill -9 13586

```

