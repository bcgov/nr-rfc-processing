import datetime

def check_date(date: str):
    format = '%Y.%m.%d'
    try:
        datetime.datetime.strptime(date, format)
        return True
    except:
        return False