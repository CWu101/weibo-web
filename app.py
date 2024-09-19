from flask import Flask, render_template, jsonify, request
import requests
from lxml import etree
import jieba
import csv
import os
import re
from datetime import datetime
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

# 当前时间
now = datetime.now()

def save(name, link, hot, tag):
    os.makedirs("Today/storage", exist_ok=True)
    os.makedirs(f"Today/storage/{now.year}-{now.month}-{now.day}", exist_ok=True)
    with open(f"Today/storage/{now.year}-{now.month}-{now.day}/hotboard-{now.year}-{now.month}-{now.day}.csv", "w", encoding='utf-8', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['name', 'link', 'hot', 'tag'])  # CSV 列名
        writer.writerows(zip(name, link, hot, tag))

def check(text):
    seg_list = jieba.cut(text, cut_all=False)
    with open('ciku.txt', 'r', encoding='utf-8') as f:
        keywords = set(f.read().splitlines())
    return any(word in keywords for word in seg_list)

def get_weibo_hot_search():
    url = "https://s.weibo.com/top/summary"
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36",
        'cookie': "SUB=_2AkMR8UCpf8NxqwFRmfwczm3mbY1zwgjEieKnrbFyJRMxHRl-yT9vqhQutRB6OnFuRoO5eDDbAe602sD9Ib0ymiYzg9PJ; SUBP=0033WrSXqPxfM72-Ws9jqgMF55529P9D9WWry_f8qSRn9eIgxf.Sk2kR; SINAGLOBAL=8502401713142.307.1722666912265; _s_tentry=-; Apache=1488716626397.5994.1726711933155; ULV=1726711933319:2:1:1:1488716626397.5994.1726711933155:1722666912270"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Check for HTTP request errors
        html_obj = etree.HTML(response.content)
        name_list = html_obj.xpath('//td/span/preceding-sibling::a/text()')
        link_list = html_obj.xpath('//td/span/preceding-sibling::a/@href')
        hot_list = html_obj.xpath('//td//span/text()')

        if len(name_list) != len(link_list) or len(link_list) != len(hot_list):
            raise ValueError("The length of name_list, link_list, and hot_list are not equal")

        topics_with_link_and_hot = []
        for name, add, hot in zip(name_list, link_list, hot_list):
            matches = re.findall(r'\d+', hot)
            hot_number = int(matches[0]) if matches else 0
            topics_with_link_and_hot.append((name, f"https://s.weibo.com{add}", hot_number))

        return topics_with_link_and_hot

    except requests.RequestException as e:
        print(f"HTTP request error: {e}")
        return []
    except ValueError as e:
        print(f"Value error: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

def generate_wordcloud(text):
    wordcloud = WordCloud(font_path='simsun.ttc', width=800, height=400).generate(text)
    img = io.BytesIO()
    wordcloud.to_image().save(img, format='PNG')
    img.seek(0)
    return base64.b64encode(img.getvalue()).decode()

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        topics = get_weibo_hot_search()
        if not topics:
            return jsonify({'error': 'Failed to fetch data'}), 500

        names, links, hots = zip(*[(name, link, hot) for name, link, hot in topics])
        text = ' '.join(names)
        wordcloud_image = generate_wordcloud(text)
        return jsonify({
            'topics': [{'name': name, 'link': link, 'hot': hot} for name, link, hot in topics],
            'wordcloud': wordcloud_image
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=False)
