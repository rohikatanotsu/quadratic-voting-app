# Quadratic Voting App

これは、Quadratic Votingの原則に基づいた投票アプリケーションです。

## 概要

このアプリケーションは2つの部分から構成されています。

*   `voting_app.py`: ユーザーが投票を行うためのStreamlitアプリケーションです。
*   `votes_visualization_app.py`: 投票結果を可視化するためのStreamlitアプリケーションです。

## 必要なもの

*   Python 3.8+
*   pip

## 使い方

1.  **リポジリをクローンします。**

    ```bash
    git clone <repository-url>
    cd quadratic-voting-app
    ```

2.  **必要なライブラリをインストールします。**

    ```bash
    pip install -r requirements.txt
    ```

3.  **投票アプリケーションを実行します。**

    ```bash
    streamlit run voting_app.py
    ```

4.  **可視化アプリケーションを実行します。**

    ```bash
    streamlit run votes_visualization_app.py
    ```

## 設定

投票の選択肢やクレジット数は `config.json` ファイルで設定できます。

```json
{
  "title": "チームの次のイベントを選ぼう！",
  "options": [
    "温泉",
    "BBQ",
    "テーマパーク",
    "ハイキング"
  ],
  "credits": 100
}
```