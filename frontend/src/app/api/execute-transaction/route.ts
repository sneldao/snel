import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const txData = await request.json();

    // For API routes in Next.js, we're just passing the transaction data back to the client
    // The actual transaction execution will happen on the client side via the wallet
    return NextResponse.json({
      success: true,
      transaction: txData,
      message: "Transaction data ready for wallet submission",
    });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: (error as Error).message },
      { status: 500 }
    );
  }
}
