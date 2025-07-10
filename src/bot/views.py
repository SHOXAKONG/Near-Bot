import telebot
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .bot_logic import bot


@csrf_exempt
def webhook_view(request):
    if request.method == 'POST':
        json_string = request.body.decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return HttpResponse(status=200)
    else:
        return HttpResponse("Webhook is active for Telebot.")
