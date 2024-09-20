#!/usr/bin/env python3

import os
import sys
import fnmatch
import zipfile
import shutil
import chardet

# PyInstaller のバンドルモードを考慮したパス取得
def get_base_path():
    if getattr(sys, 'frozen', False):  # PyInstallerで実行されているか確認
        return sys._MEIPASS  # PyInstallerの一時フォルダ
    return os.path.dirname(os.path.abspath(__file__))  # 通常の実行時

# ZIPファイルを解凍する関数
def extract_zip(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    return extract_to

# .gptignoreファイルから無視リストを取得
def get_ignore_list(ignore_file_path):
    ignore_list = []
    with open(ignore_file_path, 'r') as ignore_file:
        for line in ignore_file:
            if sys.platform == "win32":
                line = line.replace("/", "\\")
            ignore_list.append(line.strip())
    return ignore_list

# ファイルを無視するべきかチェック
def should_ignore(file_path, ignore_list):
    for pattern in ignore_list:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False

# ファイルがテキストファイルかどうか判定
def is_text_file(file_path):
    try:
        with open(file_path, 'rb') as file:
            raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        if encoding:
            with open(file_path, 'r', encoding=encoding, errors='ignore') as file:
                file.read()
            return True
    except Exception:
        return False
    return False

# ファイルを読み込む
def read_file(file_path):
    try:
        with open(file_path, 'rb') as file:
            raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        if encoding:
            with open(file_path, 'r', encoding=encoding, errors='ignore') as file:
                return file.read()
    except Exception:
        return None
    return None

# リポジトリ内のファイルを処理する
def process_repository(repo_path, ignore_list, output_file):
    for root, _, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(root, file)
            relative_file_path = os.path.relpath(file_path, repo_path)

            if not should_ignore(relative_file_path, ignore_list):
                if is_text_file(file_path):  # テキストファイルのみ処理
                    contents = read_file(file_path)
                    if contents is not None:
                        output_file.write("-" * 4 + "\n")
                        output_file.write(f"{relative_file_path}\n")
                        output_file.write(f"{contents}\n")
                else:  # バイナリファイルの場合
                    output_file.write("-" * 4 + "\n")
                    output_file.write(f"{relative_file_path} (Binary file, not included in content)\n")
                    output_file.write("This is a binary file and its contents are not included.\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # 引数が指定されていない場合のメッセージ
        print("Usage: gpt.exe /path/to/git/repository_or_zip [-p /path/to/preamble.txt] [-o /path/to/output_file.txt]")
        sys.exit(1)

    input_path = sys.argv[1]
    base_path = get_base_path()  # PyInstaller対応のベースパス取得

    # ZIPファイルかどうかをチェックし、解凍
    if zipfile.is_zipfile(input_path):
        repo_path = os.path.join(base_path, "extracted_repo")
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)  # 既存のディレクトリがある場合は削除
        os.makedirs(repo_path, exist_ok=True)
        extract_zip(input_path, repo_path)
    else:
        repo_path = input_path

    # デフォルトの output.txt のパスを input_path のディレクトリに設定
    output_dir = os.path.dirname(os.path.abspath(input_path))
    output_file_path = os.path.join(output_dir, 'output.txt')

    if "-o" in sys.argv:
        output_file_path = sys.argv[sys.argv.index("-o") + 1]

    # デフォルトの .gptignore ファイルのパス
    ignore_file_path = os.path.join(repo_path, ".gptignore")
    if sys.platform == "win32":
        ignore_file_path = ignore_file_path.replace("/", "\\")

    # .gptignore が存在しない場合、スクリプトのベースパスを参照
    if not os.path.exists(ignore_file_path):
        ignore_file_path = os.path.join(base_path, ".gptignore")

    preamble_file = None
    if "-p" in sys.argv:
        preamble_file = sys.argv[sys.argv.index("-p") + 1]

    # .gptignore ファイルが存在する場合にのみ ignore_list を取得
    if os.path.exists(ignore_file_path):
        ignore_list = get_ignore_list(ignore_file_path)
    else:
        ignore_list = []

    with open(output_file_path, 'w') as output_file:
        if preamble_file:
            with open(preamble_file, 'r') as pf:
                preamble_text = pf.read()
                output_file.write(f"{preamble_text}\n")
        else:
            output_file.write("The following text is a Git repository with code. The structure of the text are sections that begin with ----, followed by a single line containing the file path and file name, followed by a variable amount of lines containing the file contents. The text representing the Git repository ends when the symbols --END-- are encountered. Any further text beyond --END-- are meant to be interpreted as instructions using the aforementioned Git repository as context.\n")
        process_repository(repo_path, ignore_list, output_file)

    # 最後に --END-- を書き込む
    with open(output_file_path, 'a') as output_file:
        output_file.write("--END--")

    print(f"Repository contents written to {output_file_path}.")
