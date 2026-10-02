import 'reflect-metadata';
import { randomUUID } from 'node:crypto';
import { Controller, Get, Headers, HttpException, Module } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';

const gateway = process.env.OMNIAI_GATEWAY_URL ?? 'http://127.0.0.1:8090';
const upstreamTimeoutMs = Number(process.env.OMNIAI_UPSTREAM_TIMEOUT_MS ?? 5000);

@Controller()
class AppController {
  @Get('/health')
  health(@Headers('x-request-id') incomingId?: string) {
    return { ok: true, service: 'omniai-bff-nest', version: '0.1.0', request_id: incomingId ?? randomUUID(), runtime: 'node/nestjs', gateway };
  }

  @Get('/api/v1/platform/summary')
  async summary(@Headers('x-request-id') incomingId?: string) {
    const requestId = incomingId ?? randomUUID();
    const fetchGateway = async (path: string) => {
      const response = await fetch(`${gateway}${path}`, {
        headers: { 'x-request-id': requestId },
        signal: AbortSignal.timeout(upstreamTimeoutMs),
      });
      if (!response.ok) throw new Error(`gateway returned ${response.status}`);
      return response.json();
    };
    try {
      const [health, modules] = await Promise.all([
        fetchGateway('/api/v1/health'),
        fetchGateway('/api/v1/platform/modules'),
      ]);
      return { request_id: requestId, health, modules };
    } catch {
      throw new HttpException({ error: { code: 'UPSTREAM_UNAVAILABLE', message: 'gateway request failed', request_id: requestId } }, 503);
    }
  }
}

@Module({ controllers: [AppController] })
class AppModule {}

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  await app.listen(Number(process.env.PORT ?? 8093), '0.0.0.0');
}

void bootstrap();
