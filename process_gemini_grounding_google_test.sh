curl -X POST http://localhost:8081/xxx/process_gemini_grounding_google \
     -H "Authorization: Bearer xxxx" \
     -H "Content-Type: application/json" \
     -d '{
           "prompt": "アンドドット株式会社の会社情報、ホームページURL、代表者名、設立日、従業員数について調べてください。"
         }' | jq .
