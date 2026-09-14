# -*- coding:UTF-8 -*-
import json

from blueapps.account.decorators import login_exempt
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from backend.db_services.mysql.sqlparse.exceptions import SQLParseBaseException
from backend.db_services.mysql.sqlparse.handlers import SQLParseHandler


@login_exempt
@csrf_exempt
def parse_sql(request):
    sql = json.loads(request.body.decode()).get("content", "")
    try:
        return JsonResponse(SQLParseHandler().parse_sql(sql=sql))
    except SQLParseBaseException as exc:
        return JsonResponse({"result": False, "code": exc.code, "message": exc.message, "data": None})
