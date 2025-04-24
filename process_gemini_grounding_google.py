import os
import json
import hashlib
from google.cloud import storage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import vertexai

from google import genai
from google.genai import types

from google.auth import default

MAX_RETRY_COUNT = 3

def process_gemini(prompt):
    
    scopes = [
    "https://www.googleapis.com/auth/generative-language",
    "https://www.googleapis.com/auth/cloud-platform",
    ]

    credentials, _ = default(scopes=scopes)
    
    client = genai.Client(
        vertexai=True,
        project="dummy-project",
        location="us-central1",
        credentials=credentials,
    )

    model = "gemini-2.0-flash-001"
    contents = [
        types.Content(
        role="user",
        parts=[
            types.Part.from_text(prompt)
        ]
        )
    ]
    tools = [
        types.Tool(google_search=types.GoogleSearch())
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature = 0.2,
        top_p = 0.95,
        max_output_tokens = 8192,
        frequency_penalty=1.0,
        response_modalities = ["TEXT"],
        safety_settings = [types.SafetySetting(
        category="HARM_CATEGORY_HATE_SPEECH",
        threshold="OFF"
        ),types.SafetySetting(
        category="HARM_CATEGORY_DANGEROUS_CONTENT",
        threshold="OFF"
        ),types.SafetySetting(
        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
        threshold="OFF"
        ),types.SafetySetting(
        category="HARM_CATEGORY_HARASSMENT",
        threshold="OFF"
        )],
        tools = tools,
    )
    
    result_text = ""

    response = client.models.generate_content(
        model = model,
        contents = contents,
        config = generate_content_config,
        )

    for chunk in response.candidates[0].content.parts:
        result_text += str(chunk)

    grounding_search_sources = response.candidates[0].grounding_metadata.grounding_chunks
    
    grounding_search_sources_text = ""
    reference_links = {}
    no = 0
    if grounding_search_sources:
        for grounding_search_source in grounding_search_sources:
            title = grounding_search_source.web.title
            uri = grounding_search_source.web.uri
            no += 1
            reference_links[str(no)] = {"title": title, "url": uri}
            grounding_search_sources_text += f"""
Reference No.{no}, title: {title}, url: {uri}        
"""     

    # テキスト内の[数字]を対応するURLへのリンクに置き換える
    # 例: [1] -> <a href="URL1">1</a>
    result_text_with_links = result_text
    for ref_num, ref_data in reference_links.items():
        # Markdown形式のリンクに変換
        result_text_with_links = result_text_with_links.replace(
            f"[{ref_num}]", 
            f'[{ref_num}]({ref_data["url"]})'
        )
        result_text_with_links = result_text_with_links.replace(
            f"[{ref_num},", 
            f'[{ref_num}]({ref_data["url"]}),'
        )

    # 参照情報もMarkdown形式に変換
    grounding_search_sources_markdown = ""
    if reference_links:
        grounding_search_sources_markdown += "## 参照情報\n\n"
        for ref_num, ref_data in reference_links.items():
            grounding_search_sources_markdown += f"{ref_num}. [{ref_data['title']}]({ref_data['url']})\n"

    return result_text_with_links

def process_gemini_grounding_google(request):
    if request.method == "POST":
        data = json.loads(request.body.decode('utf-8'))

        # 精度改善のためにsuffix promptをつける
        prompt = data["prompt"] + "について、Google検索を用いて複数のページを調べて確実に回答してください。"

        print("prompt: ", prompt)

        retry_count = 0
        while retry_count < MAX_RETRY_COUNT:
            try:
                result = process_gemini(prompt)
                return JsonResponse({'result': result})
            except Exception as e:
                import traceback
                print(traceback.format_exc())
                retry_count += 1
                if retry_count >= MAX_RETRY_COUNT:
                    return JsonResponse({"message": str(e)}, status=500)
    else:
        return JsonResponse({"message": "Invalid method"}, status=405)


