import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

/** jsdom não tem EventSource, e o useJob abre um quando há trabalho em
 * andamento. O dublê registra a assinatura sem tocar na rede. */
class EventSourceFalso {
  static instancias: EventSourceFalso[] = [];
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  fechado = false;

  constructor(readonly url: string) {
    EventSourceFalso.instancias.push(this);
  }

  close() {
    this.fechado = true;
  }

  emitir(dados: unknown) {
    this.onmessage?.(new MessageEvent("message", {
      data: JSON.stringify(dados),
    }));
  }
}

vi.stubGlobal("EventSource", EventSourceFalso);

afterEach(() => {
  cleanup();
  EventSourceFalso.instancias.length = 0;
  vi.restoreAllMocks();
});

export { EventSourceFalso };
