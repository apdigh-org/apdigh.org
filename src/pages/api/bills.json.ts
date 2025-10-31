import type { APIRoute } from 'astro';
import { getAllBills } from '../../utils/bills';

export const GET: APIRoute = async () => {
  const bills = await getAllBills();

  return new Response(JSON.stringify(bills), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, max-age=300' // Cache for 5 minutes
    }
  });
};
