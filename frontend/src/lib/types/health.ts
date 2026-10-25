export interface HealthStatus {
  status: 'UP' | 'DOWN' | string;
  service: string;
  environment: string;
  architecture: string;
  version: string;
  pipelines: {
    attendance: string;
    infrastructure: string;
    compliance_engine: string;
    privacy_engine: string;
    [key: string]: string;
  };
}
