import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SpeechDisplay } from "@/components/mirror/SpeechDisplay";

describe("SpeechDisplay", () => {
  it("renders text content", () => {
    render(<SpeechDisplay text="Hello from Mira!" visible={true} />);
    expect(screen.getByText("Hello from Mira!")).toBeDefined();
  });

  it("has opacity 1 when visible is true", () => {
    const { container } = render(
      <SpeechDisplay text="Visible text" visible={true} />,
    );
    const div = container.firstElementChild as HTMLElement;
    expect(div.style.opacity).toBe("1");
  });

  it("has opacity 0 when visible is false", () => {
    const { container } = render(
      <SpeechDisplay text="Hidden text" visible={false} />,
    );
    const div = container.firstElementChild as HTMLElement;
    expect(div.style.opacity).toBe("0");
  });

  it("updates text on rerender", () => {
    const { rerender } = render(
      <SpeechDisplay text="First sentence." visible={true} />,
    );
    expect(screen.getByText("First sentence.")).toBeDefined();

    rerender(<SpeechDisplay text="Second sentence." visible={true} />);
    expect(screen.getByText("Second sentence.")).toBeDefined();
  });

  it("renders empty string without crashing", () => {
    const { container } = render(
      <SpeechDisplay text="" visible={true} />,
    );
    expect(container.firstElementChild).toBeDefined();
  });
});
