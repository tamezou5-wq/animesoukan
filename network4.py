import streamlit as st
import pandas as pd
import os
import uuid
import base64
from pyvis.network import Network
import unicodedata
import chardet  # これが必須です！
import io       # これも必須です！

st.title("🏫アニメ・漫画 相関図ジェネレーター")

csv_file = st.file_uploader("関係図CSVをアップロード(。´･ω･)?", type=["csv", "tsv", "txt"], label_visibility="visible")
image_files = st.file_uploader("顔画像フォルダの中身（png, jpg, jpeg）を全てアップロード(*´з`)", accept_multiple_files=True)

# --- 1. まず先に画像を処理して image_data_map を作る ---
image_data_map = {}
if image_files:
    import unicodedata # ここでインポートしておく
    valid_extensions = ('.png', '.jpg', '.jpeg')
    for img in image_files:
        if img.name.lower().endswith(valid_extensions):
            b64_image = base64.b64encode(img.read()).decode('utf-8')
            # 拡張子を除去し、名前を「正規化（NFKC）」して辞書のキーにする
            raw_name = os.path.splitext(img.name)[0]
            name = unicodedata.normalize('NFKC', raw_name) 
            image_data_map[name] = f"data:image/jpeg;base64,{b64_image}"

if csv_file and image_files:
    user_id = str(uuid.uuid4())
    
    # 3. CSV/TSV読み込みの確実化
    try:
        # ファイルの中身をバイナリとして読み込み、文字コードを判定
        raw_data = csv_file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        
        # 判定した文字コードで読み込み（タブかカンマか自動判定）
        # io.BytesIOを使用して、読み込んだバイナリデータをファイルのように扱う
        import io
        csv_file_io = io.BytesIO(raw_data)
        df = pd.read_csv(csv_file_io, sep=None, encoding=encoding, engine='python')
        
        # 列名の掃除
        df.columns = df.columns.str.strip()
        
        # 文字列の正規化
        df = df.map(lambda x: unicodedata.normalize('NFKC', str(x)) if isinstance(x, str) else x)
        df = df.replace(r'[\x00-\x1F\x7F]', '', regex=True)

    except Exception as e:
        st.error(f"ファイル読み込みエラー: {e}")
        st.stop()

    # 4. 必須列のチェック
    if not all(col in df.columns for col in ['source', 'target', 'label']):
        st.error(f"CSV/TSVの列名に source, target, label が必要です。現在は: {df.columns.tolist()}")
        st.stop()
    
    
    net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white", directed=True)
    

    net.force_atlas_2based(spring_length=100, spring_strength=0.2, gravity=-100)

    
    nodes = set(df['source']).union(set(df['target']))
    for node in nodes:
        if node in image_data_map:
            # Base64データを画像としてセット
            net.add_node(node, label=node, shape='image', image=image_data_map[node], size=40)
        else:
            # 画像がない場合はオレンジのドット
            net.add_node(node, label=node, shape='dot', color='orange', size=20)
    
    for _, row in df.iterrows():
        net.add_edge(row['source'], row['target'], label=row['label'])


    # HTML生成
    html_file = f"temp_{user_id}.html"
    net.save_graph(html_file)
    
    # --- 最終手段：保存されたHTMLファイルを強引にUTF-8化する ---
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # HTMLの中にmeta charsetがない場合、強制的に追記する
    if '<meta charset="UTF-8">' not in html_content:
        html_content = html_content.replace('<head>', '<head><meta charset="UTF-8">')
    
    # 書き込み直す
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    # -----------------------------------------------------------

    st.components.v1.html(html_content, height=650)
    os.remove(html_file)
        
