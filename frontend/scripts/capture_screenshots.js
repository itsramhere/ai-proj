import puppeteer from 'puppeteer-core';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const OUTPUT_DIR = path.resolve(__dirname, '..', 'screenshots');
const ARTIFACT_DIR = 'C:\\Users\\ramst\\.gemini\\antigravity\\brain\\deeb1d0a-1b7a-452a-aa28-05eb1932c137\\screenshots';

if (!fs.existsSync(OUTPUT_DIR)) fs.mkdirSync(OUTPUT_DIR, { recursive: true });
if (!fs.existsSync(ARTIFACT_DIR)) fs.mkdirSync(ARTIFACT_DIR, { recursive: true });

function copyToArtifact(fileName) {
  const src = path.join(OUTPUT_DIR, fileName);
  const dst = path.join(ARTIFACT_DIR, fileName);
  fs.copyFileSync(src, dst);
  console.log(`[Copied] ${fileName}`);
}

async function run() {
  console.log('Launching browser for screenshot capture...');
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    defaultViewport: { width: 1440, height: 960, deviceScaleFactor: 2 },
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();

  try {
    // ----------------------------------------------------
    // Figure 3: Dashboard and URL submission
    // ----------------------------------------------------
    console.log('Capturing Figure 3: Dashboard and URL submission...');
    await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0', timeout: 30000 });
    await new Promise(r => setTimeout(r, 1500));
    
    // Type URL so input is highlighted
    const inputSelector = 'input[type="url"]';
    if (await page.$(inputSelector)) {
      await page.type(inputSelector, 'https://www.youtube.com/watch?v=kCC40qPZq9I');
    }
    
    const fig3Path = path.join(OUTPUT_DIR, 'Figure_3_Dashboard_URL_Submission.png');
    await page.screenshot({ path: fig3Path, fullPage: false });
    copyToArtifact('Figure_3_Dashboard_URL_Submission.png');

    // ----------------------------------------------------
    // Figure 4: Processed lecture card
    // ----------------------------------------------------
    console.log('Capturing Figure 4: Processed lecture card...');
    await page.$eval(inputSelector, el => el.value = '').catch(() => {});
    
    // Select first lecture card in grid
    const cards = await page.$$('.grid > div');
    const fig4Path = path.join(OUTPUT_DIR, 'Figure_4_Processed_Lecture_Card.png');
    if (cards.length > 0) {
      await cards[0].screenshot({ path: fig4Path });
    } else {
      await page.screenshot({ path: fig4Path });
    }
    copyToArtifact('Figure_4_Processed_Lecture_Card.png');

    // ----------------------------------------------------
    // Figure 8: Power Governor (normal and simulated critical mode)
    // ----------------------------------------------------
    console.log('Capturing Figure 8: Power Governor...');
    // Scroll to bottom
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await new Promise(r => setTimeout(r, 1000));

    // Reset power state
    await fetch('http://127.0.0.1:8000/system/power/simulate-discharge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ simulate: false })
    }).catch(() => {});
    await new Promise(r => setTimeout(r, 1500));

    // Capture Power Governor (second card in the telemetry 3-col grid)
    const telemetryCards = await page.$$('.grid.grid-cols-1.lg\\:grid-cols-3 > div');
    const fig8NormalPath = path.join(OUTPUT_DIR, 'Figure_8_Power_Governor_Normal.png');
    if (telemetryCards.length >= 2) {
      await telemetryCards[1].screenshot({ path: fig8NormalPath });
    } else {
      await page.screenshot({ path: fig8NormalPath });
    }
    copyToArtifact('Figure_8_Power_Governor_Normal.png');

    // Trigger critical battery
    console.log('Triggering simulated critical battery mode...');
    await fetch('http://127.0.0.1:8000/system/power/simulate-discharge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ simulate: true })
    }).catch(() => {});
    await new Promise(r => setTimeout(r, 2000));

    const fig8CritPath = path.join(OUTPUT_DIR, 'Figure_8_Power_Governor_Critical.png');
    const telemetryCardsUpdated = await page.$$('.grid.grid-cols-1.lg\\:grid-cols-3 > div');
    if (telemetryCardsUpdated.length >= 2) {
      await telemetryCardsUpdated[1].screenshot({ path: fig8CritPath });
    } else {
      await page.screenshot({ path: fig8CritPath });
    }
    copyToArtifact('Figure_8_Power_Governor_Critical.png');

    // Reset power state
    await fetch('http://127.0.0.1:8000/system/power/simulate-discharge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ simulate: false })
    }).catch(() => {});

    // ----------------------------------------------------
    // Figure 9: Thermal Governor (normal and simulated spike mode)
    // ----------------------------------------------------
    console.log('Capturing Figure 9: Thermal Governor...');
    await fetch('http://127.0.0.1:8000/system/thermal/simulate-spike', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ simulate: false })
    }).catch(() => {});
    await new Promise(r => setTimeout(r, 1500));

    const fig9NormalPath = path.join(OUTPUT_DIR, 'Figure_9_Thermal_Governor_Normal.png');
    const thermCards = await page.$$('.grid.grid-cols-1.lg\\:grid-cols-3 > div');
    if (thermCards.length >= 1) {
      await thermCards[0].screenshot({ path: fig9NormalPath });
    } else {
      await page.screenshot({ path: fig9NormalPath });
    }
    copyToArtifact('Figure_9_Thermal_Governor_Normal.png');

    // Trigger spike mode
    console.log('Triggering simulated thermal spike (82.5 C)...');
    await fetch('http://127.0.0.1:8000/system/thermal/simulate-spike', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ simulate: true })
    }).catch(() => {});
    await new Promise(r => setTimeout(r, 2000));

    const fig9SpikePath = path.join(OUTPUT_DIR, 'Figure_9_Thermal_Governor_Spike.png');
    const thermCardsUpdated = await page.$$('.grid.grid-cols-1.lg\\:grid-cols-3 > div');
    if (thermCardsUpdated.length >= 1) {
      await thermCardsUpdated[0].screenshot({ path: fig9SpikePath });
    } else {
      await page.screenshot({ path: fig9SpikePath });
    }
    copyToArtifact('Figure_9_Thermal_Governor_Spike.png');

    // Reset thermal spike
    await fetch('http://127.0.0.1:8000/system/thermal/simulate-spike', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ simulate: false })
    }).catch(() => {});

    // ----------------------------------------------------
    // Figure 5: Notes / diagram view
    // ----------------------------------------------------
    console.log('Capturing Figure 5: Notes / diagram view...');
    await page.goto('http://localhost:5173/lectures/1', { waitUntil: 'networkidle0', timeout: 30000 });
    await new Promise(r => setTimeout(r, 3000));

    const fig5Path = path.join(OUTPUT_DIR, 'Figure_5_Notes_Diagram_View.png');
    await page.screenshot({ path: fig5Path, fullPage: false });
    copyToArtifact('Figure_5_Notes_Diagram_View.png');

    // ----------------------------------------------------
    // Figure 7: Lecture chat exchange
    // ----------------------------------------------------
    console.log('Capturing Figure 7: Lecture chat exchange...');
    // Type question and send
    const chatInput = await page.$('textarea');
    if (chatInput) {
      await chatInput.type('What are the key benefits of KV Cache in LLMs?');
      await new Promise(r => setTimeout(r, 300));
      await page.keyboard.press('Enter');
      console.log('Waiting for AI lecture tutor response...');
      await new Promise(r => setTimeout(r, 6000));
    }

    const fig7Path = path.join(OUTPUT_DIR, 'Figure_7_Lecture_Chat_Exchange.png');
    // Find chat container
    const chatContainer = await page.$('.bg-white.rounded-2xl.border.border-slate-200\\/90');
    if (chatContainer) {
      await chatContainer.screenshot({ path: fig7Path });
    } else {
      await page.screenshot({ path: fig7Path, fullPage: false });
    }
    copyToArtifact('Figure_7_Lecture_Chat_Exchange.png');

    // ----------------------------------------------------
    // Figure 6: Quiz view
    // ----------------------------------------------------
    console.log('Capturing Figure 6: Quiz view...');
    await page.goto('http://localhost:5173/lectures/1/quiz', { waitUntil: 'networkidle0', timeout: 30000 });
    await new Promise(r => setTimeout(r, 3000));

    // Click first option of question 1 if available
    const optionCards = await page.$$('.border.rounded-xl.p-3\\.5.cursor-pointer, [role="button"], button');
    if (optionCards.length > 2) {
      await optionCards[2].click().catch(() => {});
      await new Promise(r => setTimeout(r, 500));
    }

    const fig6Path = path.join(OUTPUT_DIR, 'Figure_6_Quiz_View.png');
    await page.screenshot({ path: fig6Path, fullPage: false });
    copyToArtifact('Figure_6_Quiz_View.png');

    // ----------------------------------------------------
    // Figure 10: Exported PDF
    // ----------------------------------------------------
    console.log('Capturing Figure 10: Exported PDF document...');
    // We render test_lecture_1.pdf or the notes exported directly in the browser
    const pdfPath = path.resolve(__dirname, '..', 'test_lecture_1.pdf');
    await page.goto(`file://${pdfPath}`, { waitUntil: 'networkidle0', timeout: 30000 });
    await new Promise(r => setTimeout(r, 2000));

    const fig10Path = path.join(OUTPUT_DIR, 'Figure_10_Exported_PDF.png');
    await page.screenshot({ path: fig10Path, fullPage: false });
    copyToArtifact('Figure_10_Exported_PDF.png');

    console.log('ALL FIGURES CAPTURED SUCCESSFULLY!');
  } finally {
    await browser.close();
  }
}

run().catch(err => {
  console.error('Fatal error during capture:', err);
  process.exit(1);
});
