#!/usr/bin/env python3
"""ISBN 校验、格式化与查询工具 v1.2"""

import re
import sys
import json
import urllib.request
import urllib.error


def validate_isbn(isbn: str) -> dict:
    """校验 ISBN-10 或 ISBN-13"""
    clean = re.sub(r'[-\s]', '', isbn.strip())
    result = {"original": isbn, "clean": clean, "valid": False, "type": None, "error": None}

    if len(clean) == 10:
        result["type"] = "ISBN-10"
        result["valid"] = _check_isbn10(clean)
    elif len(clean) == 13:
        result["type"] = "ISBN-13"
        result["valid"] = _check_isbn13(clean)
    else:
        result["error"] = f"长度错误: {len(clean)}位（应为10或13位）"

    return result


def _check_isbn10(s: str) -> bool:
    if not re.match(r'^\d{9}[\dXx]$', s):
        return False
    total = sum((10 - i) * (int(c) if c not in 'Xx' else 10) for i, c in enumerate(s))
    return total % 11 == 0


def _check_isbn13(s: str) -> bool:
    if not re.match(r'^\d{13}$', s):
        return False
    weights = [1, 3] * 6 + [1]
    total = sum(int(c) * w for c, w in zip(s, weights))
    return total % 10 == 0


def format_isbn(isbn: str) -> str:
    """格式化 ISBN 为标准连字符形式"""
    clean = re.sub(r'[-\s]', '', isbn.strip())
    if len(clean) == 13:
        return f"{clean[:3]}-{clean[3]}-{clean[4:8]}-{clean[8:12]}-{clean[12]}"
    elif len(clean) == 10:
        return f"{clean[0]}-{clean[1:5]}-{clean[5:9]}-{clean[9]}"
    return isbn


def lookup_isbn(isbn: str) -> dict:
    """通过 Open Library API 查询 ISBN 信息"""
    clean = re.sub(r'[-\s]', '', isbn.strip())
    url = f"https://openlibrary.org/isbn/{clean}.json"
    result = {"isbn": isbn, "found": False, "title": None, "authors": None,
              "publishers": None, "publish_date": None, "error": None}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "find-book-skill/1.2"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            result["found"] = True
            result["title"] = data.get("title", "")
            # Authors
            authors = data.get("authors", [])
            if authors:
                author_keys = [a.get("key", "") for a in authors]
                author_names = []
                for key in author_keys[:3]:
                    try:
                        a_url = f"https://openlibrary.org{key}.json"
                        a_req = urllib.request.Request(a_url, headers={"User-Agent": "find-book-skill/1.2"})
                        with urllib.request.urlopen(a_req, timeout=5) as a_resp:
                            a_data = json.loads(a_resp.read().decode())
                            author_names.append(a_data.get("name", key))
                    except Exception:
                        author_names.append(key)
                result["authors"] = author_names
            result["publishers"] = data.get("publishers", [])
            result["publish_date"] = data.get("publish_date", "")
    except urllib.error.HTTPError:
        result["error"] = "ISBN 未找到"
    except Exception as e:
        result["error"] = str(e)
    return result


def load_isbns_from_file(filepath: str) -> list:
    """从文件加载 ISBN 列表（每行一个，忽略空行和 # 注释）"""
    isbns = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                isbns.append(line)
    return isbns


def print_result(r: dict, do_lookup: bool = False):
    """格式化输出单个 ISBN 结果"""
    status = "✅" if r["valid"] else "❌"
    line = f"{status} {r['original']} → {r['type'] or 'N/A'} | 格式: {format_isbn(r['original'])}"
    if r.get("error"):
        line += f" | {r['error']}"
    print(line)

    if do_lookup and r["valid"]:
        info = lookup_isbn(r["clean"])
        if info["found"]:
            print(f"   📖 {info['title']}")
            if info["authors"]:
                print(f"   ✍️  {', '.join(info['authors'])}")
            if info["publishers"]:
                print(f"   🏢 {', '.join(info['publishers'])}")
            if info["publish_date"]:
                print(f"   📅 {info['publish_date']}")
        else:
            print(f"   ⚠️  查询失败: {info['error']}")


def main():
    args = sys.argv[1:]
    if not args:
        print("用法:")
        print("  python3 isbn_check.py <ISBN> [ISBN2 ...]        校验 ISBN")
        print("  python3 isbn_check.py --lookup <ISBN>           校验 + 查询信息")
        print("  python3 isbn_check.py --file <path>             批量校验")
        print("  python3 isbn_check.py --lookup --file <path>    批量校验 + 查询")
        sys.exit(1)

    do_lookup = False
    isbn_list = []

    # Parse args
    i = 0
    while i < len(args):
        if args[i] == "--lookup":
            do_lookup = True
        elif args[i] == "--file":
            if i + 1 >= len(args):
                print("❌ --file 需要指定文件路径")
                sys.exit(1)
            isbn_list.extend(load_isbns_from_file(args[i + 1]))
            i += 1
        else:
            isbn_list.append(args[i])
        i += 1

    if not isbn_list:
        print("❌ 未提供 ISBN")
        sys.exit(1)

    valid_count = 0
    for isbn in isbn_list:
        r = validate_isbn(isbn)
        if r["valid"]:
            valid_count += 1
        print_result(r, do_lookup)

    print(f"\n📊 共 {len(isbn_list)} 个，{valid_count} 个有效，{len(isbn_list) - valid_count} 个无效")


if __name__ == "__main__":
    main()
