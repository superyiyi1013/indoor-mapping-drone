#!/usr/bin/env python3

"""
将 ULog 日志文件上传到 logs.px4.io 服务器。

使用方法
-------
  1. 上传指定日志文件：
     .venv\\Scripts\\python.exe 03_源代码\\upload_log.py "日志文件路径.ulg"

  2. 自动扫描当前文件夹下所有 .ulg 文件上传：
     先把此脚本放到日志所在文件夹，然后运行：
     python upload_log.py

  3. 上传时附带描述（方便区分）：
     .venv\\Scripts\\python.exe 03_源代码\\upload_log.py "日志文件路径.ulg" --description "起飞后有倾斜"

  4. 静默模式（不弹交互提问）：
     .venv\\Scripts\\python.exe 03_源代码\\upload_log.py "日志文件路径.ulg" -q

注意：
  路径中有空格时一定要用双引号括起来。
  首次使用需安装依赖：py -m pip install requests

@author: Beat Kueng (beat-kueng@gmx.net)
"""


from __future__ import print_function

from argparse import ArgumentParser
import glob
import os
import subprocess
import sys

try:
    import requests
except ImportError as e:
    print("Failed to import requests: " + str(e))
    print("")
    print("You may need to install it using:")
    print("    pip3 install --user requests")
    print("")
    sys.exit(1)


quiet = False

def ask_value(text, default=None):
    """ 向用户询问某个值 """
    if quiet:
        return ""

    ask_string = '请输入' + text
    if default != None:
        ask_string += '（直接回车使用 ' + default + '）'
    ask_string += '：'
    ret = input(ask_string).strip()
    if ret == "" and default != None:
        return default
    return ret

def get_git_email():
    """ 获取 Git 全局配置的邮箱 """
    try:
        output = subprocess.check_output(["git", "config", "--global", "user.email"])
    except Exception:
        return ""

    return output.decode("utf-8").replace('\n', '')


def main():
    global quiet
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--quiet', '-q', dest='quiet', action='store_true', default=False,
            help='Quiet mode: do not ask for values which were not provided as parameters')
    parser.add_argument('--server', dest='server', type=str, default='https://logs.px4.io',
                      help='Server URL (default: https://logs.px4.io), use http://localhost:5006 for testing locally')
    parser.add_argument("--description", dest="description", type=str,
                      help="Log description", default=None)
    parser.add_argument("--feedback", dest="feedback", type=str,
                      help="Additional feedback", default=None)
    parser.add_argument("--source", dest="source", type=str,
                      help="Log source (Eg. CI)", default="webui")
    parser.add_argument("--email", dest="email", type=str,
                      help="Your e-mail (to send the upload link)", default=None)
    parser.add_argument("--type", dest="type", type=str, default='flightreport',
                        help="The upload type (either flightreport or personal).")
    parser.add_argument("--videoUrl", dest="videoUrl", type=str, default='',
                        help="An Url to a video (only used for type flightreport).")
    parser.add_argument("--rating", dest="rating", type=str, default='notset',
                        help="A rating for the flight (only used for type flightreport).")
    parser.add_argument("--windSpeed", dest="windSpeed", type=int, default=-1,
                        help="A wind speed category for the flight (only used for flightreport).")
    parser.add_argument("--public", dest="public", type=bool, default=True,
                        help="Whether the log is uploaded as public (only used for flightreport).")
    parser.add_argument("FILE", help="ULog file(s). If not provided, auto-scan current folder for *.ulg files.", nargs="*")
    args = parser.parse_args()

    # 如果没有指定文件，自动扫描脚本自身所在文件夹下所有 .ulg 文件
    files = args.FILE
    if not files:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        files = glob.glob("*.ulg")
        if not files:
            print("当前文件夹下没有找到 .ulg 文件。")
            print("请把此脚本放到日志文件夹运行，或直接传入日志文件路径：")
            print("  upload_log.py sess0001.ulg")
            return 1
        print(f"自动扫描到 {len(files)} 个日志文件:")
        for f in files:
            print(f"  {f}")
        print()

    # arguments
    quiet = args.quiet
    if args.description == None:
        description = ask_value('日志描述')
    else:
        description = args.description

    if args.feedback == None:
        feedback = ask_value('附加反馈')
    else:
        feedback = args.feedback

    if args.email == None:
        default_email = get_git_email()
        email = ask_value('邮箱地址', default_email)
    else:
        email = args.email

    server = args.server
    upload_url = server + '/upload'

    payload = {'type': args.type, 'description': description,
               'feedback': feedback, 'email': email, 'source': args.source}

    if args.type == 'flightreport':
        payload['videoUrl'] = args.videoUrl
        payload['rating'] = args.rating
        payload['windSpeed'] = args.windSpeed
        payload['public'] = str(args.public).lower()

    for file_name in files:
        if not quiet:
            print('正在上传 ' + file_name + ' ...')

        with open(file_name, 'rb') as f:
            r = requests.post(upload_url, data=payload, files={'filearg': f},
                    allow_redirects=False)
            if r.status_code == 302: # redirect
                if 'Location'  in r.headers:
                    plot_url = r.headers['Location']
                    if len(plot_url) > 0 and plot_url[0] == '/':
                        plot_url = server + plot_url
                    print('分析报告网址: ' + plot_url)


if __name__ == '__main__':
    main()
