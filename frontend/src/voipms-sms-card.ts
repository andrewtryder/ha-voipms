import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

interface VoipmsSmsCardConfig {
  type: string;
  did?: string;
  to?: string;
  title?: string;
}

type SendState = "idle" | "sending" | "success" | "error";

@customElement("voipms-sms-card")
export class VoipmsSmsCard extends LitElement {
  @property({ attribute: false }) hass: any;

  @state() private _config: VoipmsSmsCardConfig | null = null;
  @state() private _did = "";
  @state() private _to = "";
  @state() private _message = "";
  @state() private _sendState: SendState = "idle";
  @state() private _errorMessage = "";

  static getStubConfig(): Record<string, unknown> {
    return {};
  }

  setConfig(config: VoipmsSmsCardConfig) {
    if (!config) {
      throw new Error("Invalid configuration");
    }
    this._config = config;
    if (config.did) this._did = config.did;
    if (config.to) this._to = config.to;
  }

  getCardSize() {
    return 4;
  }

  static styles = css`
    :host {
      display: block;
    }
    ha-card {
      display: flex;
      flex-direction: column;
      padding: 16px;
      gap: 12px;
    }
    .header {
      font-size: 1.1em;
      font-weight: 500;
      color: var(--primary-text-color);
    }
    ha-textfield {
      width: 100%;
    }
    textarea {
      width: 100%;
      min-height: 80px;
      resize: vertical;
      box-sizing: border-box;
      font-family: inherit;
      font-size: inherit;
      padding: 10px;
      border-radius: var(--ha-border-radius, 4px);
      border: 1px solid var(--divider-color);
      background-color: var(--card-background-color);
      color: var(--primary-text-color);
    }
    .footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    .meta {
      font-size: 0.85em;
      color: var(--secondary-text-color);
    }
    .status {
      font-size: 0.85em;
      padding: 4px 8px;
      border-radius: 4px;
    }
    .status.success {
      color: var(--success-color, green);
    }
    .status.error {
      color: var(--error-color, red);
    }
    .actions {
      display: flex;
      gap: 8px;
    }
  `;

  private async _handleSend() {
    if (!this.hass || !this._to.trim() || !this._message.trim()) return;

    this._sendState = "sending";
    this._errorMessage = "";

    const data: Record<string, string> = {
      to: this._to.trim(),
      message: this._message,
    };
    if (this._did.trim()) data.did = this._did.trim();

    try {
      await this.hass.callService("voipms", "send_sms", data);
      this._sendState = "success";
      this._message = "";
    } catch (err: any) {
      this._sendState = "error";
      this._errorMessage = err?.message || "Failed to send SMS";
    }
  }

  private _renderStatus() {
    if (this._sendState === "idle") return nothing;
    if (this._sendState === "sending") {
      return html`<span class="status">Sending…</span>`;
    }
    if (this._sendState === "success") {
      return html`<span class="status success">Sent</span>`;
    }
    return html`<span class="status error"
      >${this._errorMessage || "Error"}</span
    >`;
  }

  render() {
    if (!this._config) return nothing;

    const title = this._config.title ?? "Send SMS";
    const canSend =
      this._sendState !== "sending" &&
      this._to.trim().length > 0 &&
      this._message.trim().length > 0;

    return html`
      <ha-card>
        <div class="header">${title}</div>
        <ha-textfield
          label="From DID"
          .value=${this._did}
          placeholder="default DID"
          @input=${(e: Event) =>
            (this._did = (e.target as HTMLInputElement).value)}
        ></ha-textfield>
        <ha-textfield
          label="To"
          .value=${this._to}
          placeholder="recipient number"
          @input=${(e: Event) =>
            (this._to = (e.target as HTMLInputElement).value)}
        ></ha-textfield>
        <textarea
          placeholder="Message"
          .value=${this._message}
          @input=${(e: Event) =>
            (this._message = (e.target as HTMLTextAreaElement).value)}
        ></textarea>
        <div class="footer">
          <span class="meta">${this._message.length} chars</span>
          <div class="actions">${this._renderStatus()}</div>
        </div>
        <mwc-button
          unelevated
          ?disabled=${!canSend}
          @click=${this._handleSend}
        >
          Send
        </mwc-button>
      </ha-card>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "voipms-sms-card": VoipmsSmsCard;
  }
}

(window as any).customCards = (window as any).customCards || [];
(window as any).customCards.push({
  type: "voipms-sms-card",
  name: "VoIP.MS SMS",
  description: "Send an SMS through the VoIP.MS integration",
});
