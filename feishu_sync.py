import requests
import json
from datetime import datetime

# ====================== 填入你的参数 ======================
APP_ID = "cli_aaeb5fcd9c381be4"
APP_SECRET = "mQ44mQYBgQ95EFAZDKnD9dz28yF82qZd"
BASE_APP_TOKEN = "LGPLbjHcfabcIDsxzlQcx8zfnQf"
TABLE_ID = "tblkokV3rEdH4xUN"

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
        data = resp.json()
        items = data["data"]["items"]
        all_records.extend(items)
        if not data["data"]["has_more"]:
            break
        page_token = data["data"]["page_token"]
    return all_records


def transform(records):
    output = []
    skip_count = 0
    for idx, row in enumerate(records):
        f = row["fields"]
        if idx < 2:
            print("\n=====第{}条调试信息====".format(idx+1))
            print("宴会日期原始值:", f.get(KEY_DATE))
            print("宴会厅原始值:", f.get(KEY_BANQUET_HALL))

        raw_date = f.get(KEY_DATE)
        party_date = None

        # 情况1：直接数字毫秒戳
        if isinstance(raw_date, int):
            ts = raw_date
            dt = datetime.fromtimestamp(ts / 1000)
            party_date = dt.strftime("%Y-%m-%d")
        # 情况2：数组 [时间戳, 时区]
        elif isinstance(raw_date, list) and len(raw_date) >= 1 and isinstance(raw_date[0], int):
            ts = raw_date[0]
            dt = datetime.fromtimestamp(ts / 1000)
            party_date = dt.strftime("%Y-%m-%d")
        # 情况3：已经是字符串日期
        elif isinstance(raw_date, str):
            party_date = raw_date.strip()

        banquect_hall_val = f.get(KEY_BANQUET_HALL)
        # 过滤：宴会日期为空 或者 宴会厅为空/None，都跳过不导出
        if (party_date is None or party_date == "") or (banquect_hall_val is None or str(banquect_hall_val).strip() == ""):
            skip_count += 1
            continue

        item = {
            "宴会日期": party_date,
            "档期属性": f.get(KEY_CUSTOMER),
            "预定情况": f.get(KEY_STATUS),
            "宴会厅": banquect_hall_val,
            "客户|宴会主题": f.get(KEY_THEME),
            "销售负责人": f.get(KEY_SALES),
            "桌数": f.get(KEY_TABLE_NUM)
        }
        output.append(item)

    print(f"\n⚠️跳过记录（无宴会日期 或 宴会厅为空）：{skip_count}条")
    return output


def main():
    token = get_tenant_access_token()
    raw_list = fetch_all_records(token)
    result = transform(raw_list)
    with open("feishu_data.json", "w", encoding="utf-8") as fw:
        json.dump(result, fw, ensure_ascii=False, indent=2)
    print(f"✅导出成功，一共 {len(result)} 条宴席数据 → feishu_data.json")


if __name__ == "__main__":
    main()
