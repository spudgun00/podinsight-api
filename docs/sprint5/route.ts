import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    // Get the backend API URL
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://podinsight-api.vercel.app'

    console.log(`Attempting to prewarm backend at: ${apiUrl}/api/prewarm`)

    // Forward the prewarm request to the backend
    const response = await fetch(`${apiUrl}/api/prewarm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })

    // If backend doesn't have the endpoint yet, return success anyway
    // The prewarm is optional - search will still work without it
    if (response.status === 404) {
      console.warn('Backend prewarm endpoint not found - this is optional, search will still work')
      return NextResponse.json({
        status: 'skipped',
        message: 'Prewarm endpoint not available - search will work but may have initial delay'
      })
    }

    // Return the backend response
    if (!response.ok) {
      const errorText = await response.text()
      console.error('Backend prewarm failed:', response.status, errorText)
      // Don't fail hard - prewarm is optional
      return NextResponse.json({
        status: 'error',
        message: 'Prewarm failed but search will still work',
        details: errorText
      })
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('Error calling backend prewarm:', error)
    // Don't fail hard - prewarm is optional
    return NextResponse.json({
      status: 'error',
      message: 'Prewarm failed but search will still work',
      details: error instanceof Error ? error.message : 'Unknown error'
    })
  }
}
