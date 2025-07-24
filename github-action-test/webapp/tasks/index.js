import http from 'http';

const host = "0.0.0.0";
const portNum = 3000

const server = http.createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/echo') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ message: 'echo' }));
  } else {
    res.writeHead(404);
    res.end();
  }
});

server.listen(portNum, host, () => {
  console.log(`Server is running on http://${host}:${portNum}`);
});