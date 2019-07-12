from requests_html import HTMLSession
import re

def __get_mid_text(text, left_text, right_text, start=0):#获取中间文本
    left = text.find(left_text, start)
    if left == -1:
        return ('', -1)
    left += len(left_text)
    right = text.find(right_text, left)
    if right == -1:
        return ('', -1)
    return (text[left:right], right)

def get_my_ids(session):#获取ids号
    response = session.get(
        'http://eams.uestc.edu.cn/eams/courseTableForStd.action'
    )
    response.html.render()

    data = __get_mid_text(response.html.html, '(form,"ids",\"', '\")')
    if(data[1]== -1):
        print("ids获取失败")
        exit()
    return data[0]

def get_now_semesterid(session):#获取当前学期号
    response = session.get(
        'http://eams.uestc.edu.cn/eams/teach/grade/course/person.action'
    )
    response.html.render()

    data = __get_mid_text(response.html.html, 'semesterId=', '&')
    if(data[1]== -1):
        print("semesterid获取失败")
        exit()
    ret = int(data[0])
    return ret

def get_all_course(session, semester_id = 0):#获取学期的所有课程
    #如果未输入学期号，则默认为本学期
    semester_id = get_now_semesterid(session) + 20 * semester_id
    ids = get_my_ids(session)

    form = {
        "semester.id": semester_id,
        "startWeek": "1",
        "setting.kind": "std",
        "ignoreHead": "1",
        "isEng": "0",
        "ids": ids
    }

    url = "http://eams.uestc.edu.cn/eams/courseTableForStd!courseTable.action"
    response = session.get(url, params = form)
    response.html.render()

    course_content = response.html.html
    begin = course_content.find("var activity=null;")
    end = course_content.find("table0.marshalTable")
    course_content = course_content[begin+18:end]  #对js代码进行切片，以便读取课程表

    pattern = re.compile(r"(?<=\n).*?(?=\n)")#正则表达式获取每行的字符串
    str_table = pattern.findall(course_content)

    course_info = []
    course_temp = []
    course_time = []
    for content in str_table: #枚举里面的所有字符串
        if(content.find("activity = new TaskActivity") != -1):
            if(course_temp != []):#如果之前保存了课程信息，那么就和时间一起加入人列表
                course_info.append([course_temp, course_time])
                course_time = []

            pattern = re.compile(r"(?<=\").*?(?=\")")
            t = pattern.findall(content)

            temp = []
            for c in t[12]:
                temp.append(int(c))

            course_temp = [t[6], t[2], t[10], temp,]


        elif(content.find("index =") != -1):
            a = __get_mid_text(content, "=", "*")[0] #查找上课时间
            b = __get_mid_text(content, "+", ";")[0]
            course_time.append([int(a), int(b)])

    course_info.append([course_temp, course_time]) #收尾

    return course_info