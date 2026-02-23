declare module "@cashfreepayments/cashfree-js" {
    interface CashfreeLoadOptions {
        mode: "sandbox" | "production";
    }

    interface CashfreeCheckoutOptions {
        paymentSessionId: string;
        returnUrl?: string;
        /** Callback when payment modal is closed / redirected */
        onSuccess?: (data: any) => void;
        onFailure?: (data: any) => void;
    }

    interface CashfreeInstance {
        checkout(options: CashfreeCheckoutOptions): void;
    }

    export function load(options: CashfreeLoadOptions): Promise<CashfreeInstance>;
}
