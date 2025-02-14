from datetime import datetime, date

MAX_SETS = 7            # 銘柄発掘アンケートの入力セット数
MAX_VOTE_SELECTION = 10 # 集計ページでのチェックボックスの最大選択数

def get_date_from_params(query_params):
    if 'date' in query_params:
        date_param = query_params['date'].strip()
        try:
            return datetime.strptime(date_param, "%Y%m%d").date()
        except ValueError:
            return date.today()
    return date.today() 