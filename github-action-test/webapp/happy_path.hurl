POST http://{{shim}}/test/init
{}
HTTP 200

POST http://{{shim}}/test/waitUntilInitialized
{}
HTTP 200

GET http://{{host}}/echo
HTTP 200
[Asserts]
header "Content-Type" contains "application/json"
jsonpath "$.message" == "echo"