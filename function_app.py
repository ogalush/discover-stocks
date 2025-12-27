import azure.functions as func
from datetime import datetime
import json
import logging
import os
import requests
from utils.notification import notification

app = func.FunctionApp()

## 利用に際して必要な設定 (開発時はlocal.settings.jsonへ設定)
## "CHATWORK_API_TOKEN": "xxx",
## "CHATWORK_ROOM_ID": "yyy",
## "DISCOVER_STOCKS_URI": "http://localhost:8501/",
## "SURVEY_TIMER": "0 */3 * * * *",
## "VOTE_TIMER": "0 */3 * * * *"

## URL準備
def prepareuri(baseuri, mode, date):
  uri = "%s?page=%s&date=%s" % (baseuri, mode, date)
  return uri

## 1. 銘柄登録呼びかけ
@app.timer_trigger(schedule=os.environ["SURVEY_TIMER"], arg_name="surveyTimer", run_on_startup=False, use_monitor=False) 
def information_survey(surveyTimer: func.TimerRequest) -> None:
    logging.info("surveyTimer triggered")

    ## 日付、URL取得
    mode = 'survey'
    yyyymmdd = datetime.now().strftime("%Y%m%d")
    uri = prepareuri(os.environ["DISCOVER_STOCKS_URI"], mode, yyyymmdd)
    message = "%s 銘柄登録リンク\n%s\n銘柄登録をお願いします。" % (datetime.now().strftime("%m/%d"), uri)

    ## 送信の実施
    try:
        notifier = notification(
            api_token=os.environ["CHATWORK_API_TOKEN"],
            room_id=os.environ["CHATWORK_ROOM_ID"]
        )
        notifier.post_message(message)

    except Exception as e:
        logging.exception(f"Unexpected error: {e}")

    logging.info('surveyTimer function executed.')


## 2. 投票呼びかけ
@app.timer_trigger(schedule=os.environ["VOTE_TIMER"], arg_name="voteTimer", run_on_startup=False, use_monitor=False) 
def information_vote(voteTimer: func.TimerRequest) -> None:
    logging.info("voteTimer triggered")

    ## 日付、URL取得
    mode = 'vote'
    yyyymmdd = datetime.now().strftime("%Y%m%d")
    uri = prepareuri(os.environ["DISCOVER_STOCKS_URI"], mode, yyyymmdd)
    message = "%s 銘柄投票リンク\n%s\n投票をお願いします。" % (datetime.now().strftime("%m/%d"), uri)

    ## 送信の実施
    try:
        notifier = notification(
            api_token=os.environ["CHATWORK_API_TOKEN"],
            room_id=os.environ["CHATWORK_ROOM_ID"]
        )
        notifier.post_message(message)

        ## 銘柄登録データの取得
        ## 本当はDBを直接参照したいが、SQLiteを利用しておりAppService内からしか参照できない。
        ## このためGETでCSVデータを取得する。(やろうと思ったがstreamlitから直接txtで取得できない)
        vote_csv = requests.get("https://your-app.azurewebsites.net/internal/data")

    except Exception as e:
        logging.exception(f"Unexpected error: {e}")

    logging.info('voteTimer function executed.')
