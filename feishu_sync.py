import requests
import json
from datetime import datetime

# ====================== 填入你的参数 ======================
APP_ID = "cli_aaeb5fcd9c381be4"
APP_SECRET = "mQ44mQYBgQ95EFAZDKnD9dz28yF82qZd"
BASE_APP_TOKEN = "LGPLbjHcfabcIDsxzlQcx8zfnQf"
TABLE_ID = "tblkokV3rEdH4xUN"

# 【UI显示名称】，用于去匹配拿到field_id，不要直接用于取fields字典
UI_DATE = "宴会日期"
UI_CUSTOMER = "档期属性"
UI_STATUS = "预定情况"
UI_BANQUET_HALL = "宴会厅"
UI_THEME = "客户|宴会主题"
UI_SALES = "销售负责人"
UI_TABLE_NUM = "桌数"
# ========================================================

def get_text_value(val):
    """处理飞书单选、多选、人员、引用字段，取出文本字符串"""
    if val is None:
        return ""
    if isinstance(val, list):
        tmp = []
        for i in val:
            if isinstance(i, dict):
                # 引用字段返回 {"text":"xxx"}，人员字段 {"name":"xxx"}
                tmp.append(i.get("text", i.get("name", "")))
            else:
                tmp.append(str(i))
        return ",".join(tmp)
    if isinstance(val, dict):
        return val.get("text", val.get("name", ""))
    return str(val).strip()


def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()["tenant_access_token"]


def get_field_id_map(token):
    """获取数据表所有字段：UI显示名 → field_id映射，解决含|特殊字符字段读取失败"""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_APP_TOKEN}/tables/{TABLE_ID}/fields"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    field_map = {}
    for field in data["data"]["items"]:
        ui_name = field["field_name"]
        fid = field["field_id"]
        field_map[ui_name] = fid
    print("✅字段映射表(UI名称:field_id):", json.dumps(field_map, ensure_ascii=False))
    return field_map


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


def transform(records, field_id_map):
    output = []
    skip_count = 0

    # 通过UI显示名称拿到真实field_id
    fid_date = field_id_map[UI_DATE]
    fid_customer = field_id_map[UI_CUSTOMER]
    fid_status = field_id_map[UI_STATUS]
    fid_banquet_hall = field_id_map[UI_BANQUET_HALL]
    fid_theme = field_id_map[UI_THEME]
    fid_sales = field_id_map[UI_SALES]
    fid_table_num = field_id_map[UI_TABLE_NUM]

    for idx, row in enumerate(records):
        f = row["fields"]

        raw_date = f.get(fid_date)
        party_date = None

        # 情况1：毫秒数字时间戳
        if isinstance(raw_date, int):
            ts = raw_date / 1000
            dt = datetime.utcfromtimestamp(ts + 8 * 3600)
            party_date = dt.strftime("%Y-%m-%d")
        # 情况2：飞书时间数组 [ms,offset]
        elif isinstance(raw_date, list) and len(raw_date) >= 1 and isinstance(raw_date[0], int):
            ts_ms = raw_date[0]
            offset = raw_date[1] if len(raw_date)>=2 else 8
            ts = ts_ms / 1000
            dt = datetime.utcfromtimestamp(ts + offset * 3600)
            party_date = dt.strftime("%Y-%m-%d")
        elif isinstance(raw_date, str):
            party_date = raw_date.strip()

        banquect_hall_val = get_text_value(f.get(fid_banquet_hall))

        if (party_date is None or party_date == "") or (banquect_hall_val is None or banquect_hall_val == ""):
            skip_count += 1
            continue

        item = {
            "宴会日期": party_date,
            "档期属性": get_text_value(f.get(fid_customer)),
            "预定情况": get_text_value(f.get(fid_status)),
            "宴会厅": banquect_hall_val,
            "客户 | 宴会主题": get_text_value(f.get(fid_theme)),
            "销售负责人": get_text_value(f.get(fid_sales)),
            "桌数": get_text_value(f.get(fid_table_num))
        }
        output.append(item)

    print(f"\n⚠️跳过记录（无宴会日期 或 宴会厅为空）：{skip_count} 条")
    return output


def main():
    token = get_tenant_access_token()
    # 先获取字段ID映射
    field_id_map = get_field_id_map(token)
    raw_list = fetch_all_records(token)
    result = transform(raw_list, field_id_map)
    with open("feishu_data.json", "w", encoding="utf-8") as fw:
        json.dump(result, fw, ensure_ascii=False, indent=2)
    print(f"✅导出成功，一共 {len(result)} 条宴席数据 → feishu_data.json")


if __name__ == "__main__":
    main()
