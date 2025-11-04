from flask import request

def get_lang():
    """ ดึงภาษา (en/zh) จาก query หรือ form """
    lang = (request.args.get('lang') or request.form.get('lang') or 'en').lower()
    return 'zh' if lang == 'zh' else 'en'
