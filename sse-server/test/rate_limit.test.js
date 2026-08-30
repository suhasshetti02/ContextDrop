const request = require('supertest');
const app = require('../index');

describe('SSE Server Rate Limiting', () => {
  it('should fail closed when Redis is unavailable', async () => {
    // By default, the mock or offline Redis will trigger the catch block.
    // Ensure we receive the correct error string.
    const res = await request(app).get('/stream/test_slug?q=hello');
    
    expect(res.status).toBe(200);
    expect(res.text).toContain('Error: Rate limiting service unavailable');
  });
});
