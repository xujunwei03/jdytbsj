import requests
import json
from datetime import datetime
import os

# ====================== 填入你的参数 ======================
APP_ID = os.getenv("FEISHU_APP_ID", "")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
BASE_APP_TOKEN = os.getenv("FEISHU_BITABLE_TOKEN", "")
TABLE_ID = os.getenv("FEISHU_TABLE_ID", "")

# 中文字段名（飞书多维表里的字段显示名称）
KEY_DATE = "宴会日期"
KEY_CUSTOMER = "档期属性"
KEY_STATUS = "预定情况"
KEY_BANQUET_HALL = "宴会厅"
KEY_THEME = "客户|宴会主题"
KEY_SALES = "销售负责人"
KEY_TABLE_NUM = "桌数"
# ========================================================

def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()["tenant_access_token"]


def fetch_all_records(token):
    headers = {"Authorization": f"Bearer {token}"}
    all_records = []
    page_token = None
    while True:
        params = {}
        if page_token:
            params["page_token"] = page_token
        resp = requests.get(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_APP_TOKEN}/tables/{TABLE_ID}/records",
            headers=headers,
            params=params
        )
        resp.raise_for_status()
        data = resp.json()
        items = data["data"]["items"]
        all_records.extend(items)
        if not data["data"]["has_more"]:
            break
        page_token = data["data"]["page_token"]
    return all_records


def parse_datetime_field(raw_val):
    """修复时区问题：飞书返回毫秒时间戳，强制按东八区解析，解决github服务器UTC时区偏移，日期错一天"""
    if raw_val is None:
        return None

    # 飞书日期字段标准返回格式 [1752307200000, 8]  毫秒,时区偏移小时
    if isinstance(raw_val, list) and len(raw_val)>=2 and isinstance(raw_val[0], int):
        ts_ms = raw_val[0]
        offset_h = raw_val[1]
        ts_sec = ts_ms / 1000
        # 加上时区偏移，转为北京时间
        dt = datetime.utcfromtimestamp(ts_sec + offset_h * 3600)
        return dt.strftime("%Y-%m-%d")

    # 纯数字毫秒戳
    if isinstance(raw_val, int):
        ts_sec = raw_val / 1000
        dt = datetime.utcfromtimestamp(ts_sec + 8 * 3600)
        return dt.strftime("%Y-%m-%d")

    # 字符串直接返回
    if isinstance(raw_val, str):
        s = raw_val.strip()
        return s if s else None

    return None


def get_field_text(value):
    """处理飞书各种字段类型：单选、多选、人员、文本，统一输出字符串，避免导出对象"""
    if value is None:
        return ""

    # 多选/人员：数组对象
    if isinstance(value, list):
        text_list = []
        for item in value:
            if isinstance(item, dict):
                if "text" in item:
                    text_list.append(item["text"])
                elif "name" in item:
                    text_list.append(item["name"])
            else:
                text_list.append(str(item))
        return ",".join(text_list)

    # 单选是dict
    if isinstance(value, dict):
        if "text" in value:
            return value["text"]
        elif "name" in value:
            return value["name"]

    return str(value).strip()


def transform(records):
    output = []
    skip_count = 0
    for idx, row in enumerate(records):
        f = row["fields"]

        raw_date = f.get(KEY_DATE)
        party_date = parse_datetime_field(raw_date)

        hall_text = get_field_text(f.get(KEY_BANQUET_HALL))

        # 过滤条件：宴会日期为空 OR 宴会厅为空，跳过
        if (not party_date) or (not hall_text):
            skip_count +=1
            continue

        item = {
            "宴会日期": party_date,
            "档期属性": get_field_text(f.get(KEY_CUSTOMER)),
            "预定情况": get_field_text(f.get(KEY_STATUS)),
            "宴会厅": hall_text,
            "客户|宴会主题": get_field_text(f.get(KEY_THEME)),
            "销售负责人": get_field_text(f.get(KEY_SALES)),
            "桌数": get_field_text(f.get(KEY_TABLE_NUM))
        }
        output.append(item)

    print(f"⚠️跳过记录（无宴会日期 或 宴会厅为空）：{skip_count}条")
    print(f"✅有效输出记录：{len(output)}条")
    return output


def main():
    token = get_tenant_access_token()
    raw_list = fetch_all_records(token)
    print(f"📥从飞书读取原始总记录数：{len(raw_list)}")
    result = transform(raw_list)
    with open("feishu_data.json", "w", encoding="utf-8") as fw:
        json.dump(result, fw, ensure_ascii=False, indent=2)
    print(f"✅导出成功 → feishu_data.json")


if __name__ == "__main__":
    main()
