import http from 'k6/http';
import { sleep } from 'k6';

const URL_POST = "http://localhost:30090/transactions";
const URL_GET = "http://localhost:30090/transactions";
const HEADERS = {
  "accept": "application/json",
  "Content-Type": "application/json",
};

const PAYLOAD = {
  "account_id": 1,
  "type": "INCOME",
  "amount": 5000,
  "description": "k6_test_transaction",
  "occurred_at": new Date().toISOString(),
  "category": "trabalho"
};

let requestCounter = 0;

export const options = {
  discardResponseBodies: false,
  thresholds: {
    http_req_duration: ['p(95)<1000'],
    http_req_failed: ['rate<0.02'],
  },
  scenarios: {
    spike_test: {
      executor: 'ramping-arrival-rate',
      startRate: 1,
      timeUnit: '10s',
      preAllocatedVUs: 2,
      maxVUs: 5,
      stages: [
        { target: 1, duration: '1m' },     
        { target: 10, duration: '30s' },   
        { target: 1, duration: '2m' },
        { target: 10, duration: '3m' },
        { target: 1, duration: '30s' },
      ],
    },
  },
};

function requestWithRetry(method, url, body, params, attempts = 2) {
  let res;
  for (let i = 0; i < attempts; i++) {
    if (method === 'POST') {
      res = http.post(url, body, params);
    } else {
      res = http.get(url, params);
    }

    if (res && res.status && res.status !== 0) {
      return res;
    }

    sleep(0.5);
  }

  return res;
}

export default function () {
  requestCounter++;

  let res;
  if (requestCounter % 2 === 0) {
    res = requestWithRetry('POST', URL_POST, JSON.stringify(PAYLOAD), {
      headers: HEADERS,
      tags: { name: 'POST_Transaction' },
      timeout: '20s',
    }, 2);
  } else {
    res = requestWithRetry('GET', URL_GET, null, {
      headers: HEADERS,
      tags: { name: 'GET_Transactions' },
      timeout: '20s',
    }, 2);
  }

  if (res.status !== 200 && res.status !== 201) {
    console.error(`Request failed: ${res.status} ${res.body ? res.body.slice(0,200) : ''}`);
  }

  sleep(0.01);
}
