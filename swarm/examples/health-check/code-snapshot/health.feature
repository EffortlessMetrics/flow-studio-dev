Feature: Health endpoint

  Scenario: Service returns healthy status
    Given the service is running
    When I GET /health
    Then the response status is 200
    And the response body contains {"status":"ok"}
Feature: Health endpoint

  Scenario: Service responds to health check
    Given the service is running
    When a client GETs "/health"
    Then the response status is 200
    And the response body contains JSON with "status": "ok"
