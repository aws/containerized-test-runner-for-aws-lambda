GET http://{{host}}/echo
HTTP 200
[Asserts]
header "Content-Type" contains "application/json"
jsonpath "$.message" == "echo"