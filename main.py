from time import sleep
import time, win32con, win32api, win32gui, ctypes
from pywinauto import clipboard
import pandas as pd
import openai
import os
import asyncio


model = 'gpt-3.5-turbo'
openai.api_key = os.environ['OPENAI_API_KEY']


PBYTE256 = ctypes.c_ubyte * 256
_user32 = ctypes.WinDLL("user32")
GetKeyboardState = _user32.GetKeyboardState
SetKeyboardState = _user32.SetKeyboardState
PostMessage = win32api.PostMessage
SendMessage = win32gui.SendMessage
FindWindow = win32gui.FindWindow
IsWindow = win32gui.IsWindow
GetCurrentThreadId = win32api.GetCurrentThreadId
GetWindowThreadProcessId = _user32.GetWindowThreadProcessId
AttachThreadInput = _user32.AttachThreadInput

MapVirtualKeyA = _user32.MapVirtualKeyA
MapVirtualKeyW = _user32.MapVirtualKeyW

MakeLong = win32api.MAKELONG
w = win32con


# 조합키 쓰기 위해
def PostKeyEx(hwnd, key, shift, specialkey):
    if IsWindow(hwnd):

        ThreadId = GetWindowThreadProcessId(hwnd, None)

        lparam = MakeLong(0, MapVirtualKeyA(key, 0))
        msg_down = w.WM_KEYDOWN
        msg_up = w.WM_KEYUP

        if specialkey:
            lparam = lparam | 0x1000000

        if len(shift) > 0:
            pKeyBuffers = PBYTE256()
            pKeyBuffers_old = PBYTE256()

            SendMessage(hwnd, w.WM_ACTIVATE, w.WA_ACTIVE, 0)
            AttachThreadInput(GetCurrentThreadId(), ThreadId, True)
            GetKeyboardState(ctypes.byref(pKeyBuffers_old))

            for modkey in shift:
                if modkey == w.VK_MENU:
                    lparam = lparam | 0x20000000
                    msg_down = w.WM_SYSKEYDOWN
                    msg_up = w.WM_SYSKEYUP
                pKeyBuffers[modkey] |= 128

            SetKeyboardState(ctypes.byref(pKeyBuffers))
            time.sleep(0.01)
            PostMessage(hwnd, msg_down, key, lparam)
            time.sleep(0.01)
            PostMessage(hwnd, msg_up, key, lparam | 0xC0000000)
            time.sleep(0.01)
            SetKeyboardState(ctypes.byref(pKeyBuffers_old))
            time.sleep(0.01)
            AttachThreadInput(GetCurrentThreadId(), ThreadId, False)

        else:  #  SendMessage
            SendMessage(hwnd, msg_down, key, lparam)
            SendMessage(hwnd, msg_up, key, lparam | 0xC0000000)


def kakao_sendtext(chatroom_name, text):

    hwndMain = win32gui.FindWindow( None, chatroom_name)
    hwndEdit = win32gui.FindWindowEx( hwndMain, None, "RICHEDIT50W", None)

    win32api.SendMessage(hwndEdit, win32con.WM_SETTEXT, 0, text)
    SendReturn(hwndEdit)


def SendReturn(hwnd):
    win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
    sleep(0.01)
    win32api.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)


def copy_chatroom(chatroom_name):
    # # 핸들 _ 채팅방
    hwndMain = win32gui.FindWindow( None, chatroom_name)
    hwndListControl = win32gui.FindWindowEx(hwndMain, None, "EVA_VH_ListControl_Dblclk", None)

    # #조합키, 본문을 클립보드에 복사 ( ctl + c , v )
    PostKeyEx(hwndListControl, ord('A'), [w.VK_CONTROL], False)
    time.sleep(0.5)
    PostKeyEx(hwndListControl, ord('C'), [w.VK_CONTROL], False)
    ctext = clipboard.GetData()
    # print(ctext)
    return ctext


def open_chatroom(chatroom_name):

    hwndkakao = win32gui.FindWindow(None, "카카오톡")
    hwndkakao_edit1 = win32gui.FindWindowEx( hwndkakao, None, "EVA_ChildWindow", None)
    hwndkakao_edit2_1 = win32gui.FindWindowEx( hwndkakao_edit1, None, "EVA_Window", None)
    hwndkakao_edit2_2 = win32gui.FindWindowEx( hwndkakao_edit1, hwndkakao_edit2_1, "EVA_Window", None)
    hwndkakao_edit3 = win32gui.FindWindowEx( hwndkakao_edit2_2, None, "Edit", None)

    win32api.SendMessage(hwndkakao_edit3, win32con.WM_SETTEXT, 0, chatroom_name)
    sleep(0.5)
    SendReturn(hwndkakao_edit3)
    sleep(0.5)


# # 채팅내용 초기 저장 _ 마지막 채팅
def chat_last_save():
    open_chatroom(kakao_opentalk_name)  # 채팅방 열기
    ttext = copy_chatroom(kakao_opentalk_name)  # 채팅내용 가져오기
    a = ttext.split('\r\n')  # \r\n 으로 스플릿 __ 대화내용 인용의 경우 \r 때문에 해당안됨

    df = pd.DataFrame(a)  # DF 으로 바꾸기

    df[0] = df[0].str.replace('\[([\S\s]+)\] \[(오전|오후)([0-9:\s]+)\] ', '')  # 정규식으로 채팅내용만 남기기

    return df.index[-2], df.iloc[-2, 0]


def query_chatgpt(text):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": text}
    ]

    # ChatGPT API 호출하기
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages
    )
    answer = response['choices'][0]['message']['content']
    kakao_sendtext(kakao_opentalk_name, f"{answer}")


# # 채팅방 커멘드 체크
def chat_check_command(cls, clst):
    open_chatroom(kakao_opentalk_name)  # 채팅방 열기
    ttext = copy_chatroom(kakao_opentalk_name)  # 채팅내용 가져오기

    a = ttext.split('\r\n')    # \r\n 으로 스플릿 __ 대화내용 인용의 경우 \r 때문에 해당안됨
    df = pd.DataFrame(a)  # DF 으로 바꾸기

    df[0] = df[0].str.replace('\[([\S\s]+)\] \[(오전|오후)([0-9:\s]+)\] ', '')  # 정규식으로 채팅내용만 남기기

    if df.iloc[-2, 0] == clst:
        print("채팅 없었음..")
        return df.index[-2], df.iloc[-2, 0]
    else:
        print("채팅 있었음")
        df1 = df.iloc[cls+1:,0]   # 최근 채팅내용만 남김
        print(df1)

        found = df1[df1.str.contains(chat_command)]    # 챗 카운트

        if 1 <= int(found.count()):
            print("-------커멘드 확인!")
            for i, line in enumerate(found.to_numpy()):
                query_chatgpt(line.split('베어킹봇 ')[-1])
            # 명령어 여러개 쓸경우 리턴값으로 각각 빼서 쓰면 될듯. 일단 테스트용으로 위에 하드코딩 해둠
            return df.index[-2], df.iloc[-2, 0]

        else:
            print("커멘드 미확인")
            return df.index[-2], df.iloc[-2, 0]


# # 카톡창 이름, (활성화 상태의 열려있는 창)
kakao_opentalk_name = '베어킹'
chat_command = '베어킹봇'


def main():
    cls, clst = chat_last_save()
    while True:
        print("실행중.................")

        cls, clst = chat_check_command(cls, clst)  # 커멘드 체크
        time.sleep(0.5)


if __name__ == '__main__':
    main()
