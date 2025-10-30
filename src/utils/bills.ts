import { readdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';

export interface Bill {
  id: string;
  title: string;
  status: string;
  priority: string;
  categories: string[];
  summary: string;
  impacts: Record<string, {
    score: string;
    description: string;
    relatedProvisions?: string[];
  }>;
  keyConcerns?: Array<{
    id: string;
    title: string;
    severity: string;
    description: string;
    relatedProvisions?: string[];
    relatedImpacts?: string[];
  }>;
  provisions?: Array<{
    id: string;
    section: string;
    title: string;
    plainLanguage: string;
    rawText: string;
    relatedImpacts?: string[];
  }>;
  notebookLMVideo: {
    url: string;
    duration: string;
  };
  deadline: string;
  submissionMethod: string;
  relatedBills: Array<{
    id: string;
    title: string;
    relationship: string;
  }>;
}

/**
 * Load all bills from the data/bills directory
 */
export async function getAllBills(): Promise<Bill[]> {
  const billsDir = join(process.cwd(), 'src/data/bills');

  try {
    const files = await readdir(billsDir);
    const jsonFiles = files.filter(file => file.endsWith('.json'));

    const bills = await Promise.all(
      jsonFiles.map(async (file) => {
        const filePath = join(billsDir, file);
        const content = await readFile(filePath, 'utf-8');
        return JSON.parse(content) as Bill;
      })
    );

    return bills;
  } catch (error) {
    console.error('Error loading bills:', error);
    return [];
  }
}

/**
 * Load a single bill by ID
 */
export async function getBillById(id: string): Promise<Bill | null> {
  const billsDir = join(process.cwd(), 'src/data/bills');
  const filePath = join(billsDir, `${id}.json`);

  try {
    const content = await readFile(filePath, 'utf-8');
    return JSON.parse(content) as Bill;
  } catch (error) {
    console.error(`Error loading bill ${id}:`, error);
    return null;
  }
}
