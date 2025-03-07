import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  vus: 10, // Number of virtual users
  duration: '30s', // Test duration
};

function getRandomSMILES() {
  const elements = ['C', 'N', 'O', 'Cl', 'Br', 'F'];
  let smiles = '';
  let length = Math.floor(Math.random() * 5) + 2; // Random length between 2 and 6
  for (let i = 0; i < length; i++) {
    smiles += elements[Math.floor(Math.random() * elements.length)];
  }
  return smiles;
}

export default function () {
  const payload = JSON.stringify({
    service_name: "get molecule MySimplePredictor",
    service_type: "get_molecule_property",
    parameters: {
      property_type: ["property1"],
      subjects: [getRandomSMILES()]
    }
  });

  const params = {
    headers: { 'Content-Type': 'application/json' }
  };

  let res = http.post('http://0.0.0.0:8080/service', payload, params);

  check(res, {
    'is status 200': (r) => r.status === 200,
    'is response not empty': (r) => r.body.length > 0
  });

  sleep(1);
}
