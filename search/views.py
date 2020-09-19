import json
from django.shortcuts import render
from django.views.generic.base import View
from search.models import ArticleQuestionType
from django.http import HttpResponse
from elasticsearch import Elasticsearch
from datetime import datetime

client = Elasticsearch(hosts=["127.0.0.1"])


class IndexView(View):
    # 首页
    def get(self, request):
        return render(request, "index.html")


# Create your views here.
class SearchSuggest(View):
    def get(self, request):
        key_words = request.GET.get('s', '')
        re_datas = []
        if key_words:
            s = ArticleQuestionType.search()
            s = s.suggest('my_suggest', key_words, completion={
                "field": "suggest", "fuzzy": {
                    "fuzziness": 2
                },
                "size": 10
            })
            suggestions = s.execute_suggest()
            for match in suggestions.my_suggest[0].options:
                source = match._source
                re_datas.append(source["title"])
        return HttpResponse(json.dumps(re_datas), content_type="application/json")


class SearchView(View):
    def get(self, request):
        key_words = request.GET.get("q", "")
        index_name = "article"
        page = request.GET.get("p", "1")
        try:
            page = int(page)
        except:
            page = 1

        start_time = datetime.now()
        response = client.search(
            index=index_name,
            body={
                "query": {
                    "multi_match": {
                        "query": key_words,
                        "fields": ["title"]
                    }
                },
                "from": (page - 1) * 10,
                "size": 10,
                "highlight": {
                    "pre_tags": ['<span class="keyWord">'],
                    "post_tags": ['</span>'],
                    "fields": {
                        "title": {},
                    }
                }
            }
        )

        end_time = datetime.now()
        last_seconds = (end_time - start_time).total_seconds()
        total_nums = response["hits"]["total"]
        if (page % 10) > 0:
            page_nums = int(total_nums / 10) + 1
        else:
            page_nums = int(total_nums / 10)
        hit_list = []
        for hit in response["hits"]["hits"]:
            from collections import defaultdict
            hit_dict = defaultdict(str)
            if "highlight" not in hit:
                hit["highlight"] = {}

            if "title" in hit["highlight"]:
                hit_dict["title"] = "".join(hit["highlight"]["title"])
            else:
                hit_dict["title"] = hit["_source"]["title"]

            hit_dict["content"] = hit["_source"]["content"]
            hit_dict["question_id"] = hit["_source"]["question_id"]
            hit_dict["source"] = hit["_source"]["source"]
            hit_dict["score"] = hit["_score"]
            hit_dict["answer_num"] = hit["_source"]["answer_num"]
            hit_dict["url"] = hit["_source"]["url"]

            hit_list.append(hit_dict)

        return render(request, "result.html", {"page": page,
                                               "all_hits": hit_list,
                                               "key_words": key_words,
                                               "total_nums": total_nums,
                                               "page_nums": page_nums,
                                               "index_name": index_name,
                                               "last_seconds": last_seconds})
