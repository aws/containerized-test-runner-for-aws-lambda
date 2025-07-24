import http from 'http';

// AWS_LAMBDA_HTTP_ENDPOINT environment variable format: "host:port"
const [host, port] = process.env.AWS_LAMBDA_HTTP_ENDPOINT.split(':');
const portNum = parseInt(port, 10);

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
  console.log(`Server is running on http://${host}:${port}`);
});