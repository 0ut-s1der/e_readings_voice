from vosk import Model, KaldiRecognizer
import pyttsx3
import pyaudio
import json
import mysql.connector

qst=["Назовите свой идентификационный номер","Назовите показания дневного тарифа т 1",
     "Назовите показания ночного тарифа т 2"]
app=[None for j in range(len(qst))]
day_prev=0
night_prev=0
digits={"ноль":0,"один":1, "одна":1, "два":2, "две":2,"три":3,"четыре":4,"пять":5,"шесть":6,"семь":7,
        "восемь":8,"девять":9,"десять":10,"одиннадцать":11,"двенадцать":12,
        "тринадцать":13,"четырнадцать":14,"пятнадцать":15,"шестнадцать":16,"семнадцать":17,
        "восемнадцать":18,"девятнадцать":19,"двадцать":20, "тридцать":30,"сорок":40,"пятьдесят":50,
        "шестьдесят":60,"семьдесят":70,"восемьдесят":80, "девяносто":90,"сто":100, "двести":200,
        "триста":300, "четыреста":400, "пятьсот":500, "шестьсот":600, "семьсот":700, "восемьсот":800,
        "девятьсот":900, "тысяч":1000, "тысяча":1000, "тысячи":1000}

#model = Model("model/vosk-model-ru-0.22")
model = Model("model/small_model")
rec = KaldiRecognizer(model, 8000)
p = pyaudio.PyAudio()

stream = p.open(        #Параметры потока
    format = pyaudio.paInt16,
    channels = 1,
    rate = 8000,
    input = True,
    frames_per_buffer = 8000
)

tts=pyttsx3.init()
ru_link_m="HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\RHVoice-Aleksandr-Russian"
ru_link_w="HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\RHVoice-Elena-Russian"
tts.setProperty("voice", ru_link_m)

def create_connection(host, user, passwd, database):
    conn = None
    try:
        conn = mysql.connector.connect(
            host = host,
            user = user,
            passwd = passwd,
            database = database
        )
        cursor = conn.cursor()
        add = """INSERT INTO readings(user_id) SELECT user_id FROM addresses
                 WHERE user_id NOT IN(SELECT user_id FROM readings)"""
        cursor.execute(add)
        conn.commit()
    except mysql.connector.Error as e:
        speak("Возникла ошибка с базой данных. Приношу извинения за неудобства")
        quit()
    return conn

def read_query(conn, query):
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        result = cursor.fetchone()
        return result
    except mysql.connector.Error as e:
        speak("Возникла ошибка с базой данных. Приношу извинения за неудобства")
        quit()

def insert_query(conn, query):
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        conn.commit()
        return 1
    except mysql.connector.Error as e:
        speak("Возникла ошибка при добавлении данных. Приношу извинения за неудобства")
        return 0

def write():
    global app, day_prev, night_prev
    speak("Запись данных")
    sql_i = "UPDATE readings SET day_new=" + str(app[1]) + ", night_new=" + str(app[2]) + " WHERE user_id=" + str(app[0]) + ";"
    ii = insert_query(conn, sql_i)
    if ii == 1:
        cost = round((int(app[1]) - day_prev) * 4.28 + (int(app[2]) - night_prev) * 2.36,2)
        speak("Показания успешно записаны. За текущий месяц к оплате будет" + str(
            int(cost)) + "рублей," + str(int((cost-int(cost))*100)) + "копеек. Спасибо, что пользуетесь нашими услугами")
    else:
        speak("Данные не удалось записать. Попробуйте позже.")
    stream.stop_stream()
    return

def speak(text):
    stream.stop_stream()
    tts.say(text)
    tts.runAndWait()
    stream.start_stream()
    return

def listen():
    stream.start_stream()   #Начало прослушки
    s = 0
    ss = 0
    while True:
        s+=1
        data = stream.read(4000, exception_on_overflow=False)
        if len(data) <= 0:
            break
        if rec.AcceptWaveform(data):
            ans=json.loads(rec.Result())
            if ans["text"]:
                s = 0
                ss = 0
                yield ans["text"]
        elif ss>2:
            speak("Автоматическое отключение")
            quit()
        elif s>15:
            if ss<2:
                speak("я вас слушаю")
            s = 0
            ss+=1

def to_digit(x):
    x_list = x.split()
    x_digit = ""
    x_t = 0
    x_c = 3
    for i in x_list:
        if i in digits.keys():
            if digits.get(i) == 1000:
                if x_digit=="":
                    if x_t!=0:
                        x_t=x_t*1000
                    else:
                        x_t=1000
                else:
                    x_t=int(x_digit)*1000
                    x_digit=""
                x_c=3
            elif digits.get(i) >= 100:
                if x_c != 3:
                    x_digit += str(x_t)
                    x_t = 0
                x_t += digits.get(i)
                x_c = 2
            elif digits.get(i) >= 20:
                if x_c == 1:
                    x_digit += str(x_t)
                    x_t = 0
                x_t += digits.get(i)
                x_c = 1
            elif digits.get(i) >= 10 and x_c == 1:
                x_digit += str(x_t)
                x_digit += str(digits.get(i))
                x_t = 0
                x_c = 3
            elif digits.get(i) == 0:
                if x_t!=0:
                    x_digit+=str(x_t)
                x_digit += "0"
                x_t = 0
                x_c = 3
            else:
                x_t += digits.get(i)
                x_digit += str(x_t)
                x_t = 0
                x_c = 3
        else:
            return "no_digits"
    if x_t != 0:
        x_digit += str(x_t)
    x_digit=str(int(x_digit))
    if len(x_digit)>6:
        return "err"
    return x_digit

def chk_ind(new_x):
    sql_sel = "SELECT address FROM addresses WHERE user_id=" + str(new_x)
    sql_r = read_query(conn, sql_sel)
    if sql_r == None:
        speak("Такого идентификатора нет в базе данных. Используйте действующий идентификатор")
        return 0
    else:
        speak("Ваш адрес")
        speak(sql_r)
    return conf(1)

def chk_reads(new_x):
    global day_prev, night_prev
    sql_sel = "SELECT day_new, day_prev, night_prev FROM readings WHERE user_id=" + str(new_x)
    sql_r = read_query(conn, sql_sel)
    day_prev = int(sql_r[1])
    night_prev = int(sql_r[2])
    if sql_r[0] != None:
        speak("Вы уже вносили показания. Хотите перезаписать?")
        return conf(0)
    return 1

def conf(i):
    if i:
        speak("Данные верны?")
    for x in listen():
        if x == "да":
            return 1
        elif x == "нет":
            return 0
        else:
            speak("Ответьте да или нет")
            continue

def start():
    global app,day_prev,night_prev
    i = 0
    speak("Здравствуйте. Вас приветствует голосовой ассистент.")
    while i < len(qst):
        speak(qst[i])
        for x in listen():
            x = to_digit(x)
            if x == "err":
                if i == 0:
                    speak("Идентификационный номер должен содержать не более шести цифр")
                else:
                    speak("Показания не могут иметь больше шести цифр")
                continue
            elif x == "no_digits":
                speak("Число не удалось распознать. Повторите.")
                continue
            speak(x)
            if conf(1):
                if i == 0:
                    if chk_ind(x):
                        if chk_reads(x) == 0:
                            speak("Спасибо, что пользуетесь нашими услугами")
                            return
                    else:
                        continue
                elif i == 1 and day_prev > int(x):
                    speak("Значение показаний за прошлый месяц"+str(day_prev)+". Проверьте правильность данных")
                    continue
                elif i == 2 and night_prev > int(x):
                    speak("Значение показаний за прошлый месяц" +str(night_prev)+". Проверьте правильность данных")
                    continue
                app[i] = x
                i += 1
            break
    write()
conn = create_connection("localhost","root","root", "e_readings")

















