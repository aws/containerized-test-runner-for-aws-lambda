POST http://{{shim}}/test/init
{}
HTTP 200

POST http://{{shim}}/test/waitUntilInitialized
{}
HTTP 400
[Asserts]
jsonpath "$.error.errorCategory" == "Error.Application"
jsonpath "$.error.reason" == "Application.TimeoutListenError"
jsonpath "$.error.errorMsg" == "Application.TimeoutListenError"