def ping(event, context):
  return {"msg": "pong[" + event['msg'] + "]"}