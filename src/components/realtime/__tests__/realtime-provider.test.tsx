import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { RealtimeProvider } from "@/components/realtime/realtime-provider";
import { useRealtime } from "@/hooks/useRealtime";

function StatusProbe() {
  const { status, subscribe } = useRealtime();
  // subscribe must be a no-op (not throw) while disabled.
  const sub = subscribe("reservation:1", "status", () => {});
  sub.unsubscribe();
  return <span data-testid="status">{status}</span>;
}

describe("RealtimeProvider", () => {
  it("renders children and is inert (status 'disabled') without Supabase env", () => {
    const { getByTestId } = render(
      <RealtimeProvider>
        <StatusProbe />
      </RealtimeProvider>,
    );
    expect(getByTestId("status").textContent).toBe("disabled");
  });

  it("useRealtime throws when used outside the provider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<StatusProbe />)).toThrow(
      /useRealtime must be used within/,
    );
    spy.mockRestore();
  });
});
