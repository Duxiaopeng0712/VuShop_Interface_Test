import smtplib
import time
from email.header import Header
from email.mime.text import MIMEText
import configparser
import yaml
from pymongo import MongoClient

# 获取mongoDB、email配置信息
config = configparser.ConfigParser()
config.read('config/config.ini', encoding='utf-8')

# 测试集合白名单路径
test_case_path = "config/config.yaml"


def read_yaml(path):
    """
    读取测试集合白名单文件
    :param path: 文件路径
    :return:
    """
    file = open(path)
    data = yaml.load(file, Loader=yaml.FullLoader)
    return data


def SendMail(duration):
    """
    发送邮件
    :param duration: 最大巡检时间
    :return:
    """
    mail_host = config.get("email", "host")
    mail_user = config.get("email", "user")
    mail_pass = config.get("email", "password")
    mail_sender = config.get("email", "sender")

    receivers_dict = get_receivers(duration)
    for key, value in receivers_dict.items():
        message_body = "Dear all:\n    接口巡检异常，告警信息如下：\n\n"
        for i in range(len(value)):
            body = "    -------------------------------\n\n    测试组别：{}\n    测试项目：{}\n    接口集合：{}\n\n".format(value[i][2], value[i][1], value[i][0])
            message_body += body

        tm = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        message = MIMEText(message_body, 'plain', 'utf-8')
        message['From'] = mail_user
        message['To'] = key
        subject = "接口巡检告警邮件"
        message['Subject'] = Header(subject + '_' + tm, 'utf-8')

        try:
            smtpObj = smtplib.SMTP()
            smtpObj = smtplib.SMTP_SSL(mail_host, 465)
            smtpObj.login(mail_user, mail_pass)
            smtpObj.sendmail(mail_sender, key, message.as_string())
            print('send mail ok')
        except smtplib.SMTPException:
            print('send mail fail')


def get_receivers(duration):
    """
    获取邮件发送的对象及相关内容
    :param duration:
    :return:
    """
    db_connection = MongoClient(config.get("DATABASE", "HOST"))
    datas = read_yaml(test_case_path)
    receivers_dict = {}
    print(datas)
    for i in range(len(datas)):
        group_query = {"group_name": datas[i]["group"]}
        group = db_connection["admin"]["group"].find_one(group_query)
        project_query = {"name": datas[i]["project"], "group_id": group["_id"]}
        project = db_connection["admin"]["project"].find_one(project_query)
        receivers = project["members"]
        col_query = {"name": datas[i]["test_collection"], "project_id": project["_id"]}
        for col in db_connection["admin"]["interface_col"].find(col_query):
            current_time = int(time.time())
            last_test_time = col["up_time"]
            if (current_time - last_test_time > duration):
                for j in range(len(receivers)):
                    # SendMail(col["name"], project["name"], group["group_name"], receivers[j]["email"])
                    if receivers[j]["email"] in receivers_dict.keys():
                        receivers_dict.get(receivers[j]["email"]).append(
                            [col["name"], project["name"], group["group_name"]])
                    else:
                        receivers_dict[receivers[j]["email"]] = [[col["name"], project["name"], group["group_name"]]]

    print(receivers_dict)
    return receivers_dict


if __name__ == '__main__':
    SendMail(10)
