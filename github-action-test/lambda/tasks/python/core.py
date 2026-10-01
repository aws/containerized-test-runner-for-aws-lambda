def ping(event, context):
  return {"msg": "pong[" + event['msg'] + "]"}

def echoClientContextCustom(event, context):
  custom = context.client_context.custom if context.client_context else None
  return {"custom": custom}