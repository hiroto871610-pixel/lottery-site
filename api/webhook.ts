import type { VercelRequest, VercelResponse } from '@vercel/node';
import * as line from '@line/bot-sdk';

const config = {
  channelAccessToken: process.env.LINE_CHANNEL_ACCESS_TOKEN || '',
  channelSecret: process.env.LINE_CHANNEL_SECRET || '',
};

const client = new line.messagingApi.MessagingApiClient({
  channelAccessToken: config.channelAccessToken,
});

export default async function handler(req: VercelRequest, res: VercelResponse) {
  // ブラウザからのアクセス確認用
  if (req.method === 'GET') {
    return res.status(200).json({ message: 'Webhook is running perfectly!' });
  }

  // LINE以外からの不正なアクセスを弾く
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  try {
    // LINEから送られてきたメッセージのデータ
    const events = req.body.events;

    for (const event of events) {
      if (event.type === 'message' && event.message.type === 'text') {
        const userText = event.message.text;
        let replyText = '';

        // ▼▼▼ おみくじ・予想ロジック ▼▼▼
        if (userText === 'ロト6') {
          const nums: number[] = [];
          while(nums.length < 6) {
            const n = Math.floor(Math.random() * 43) + 1;
            if(!nums.includes(n)) nums.push(n);
          }
          const sorted = nums.sort((a,b) => a - b).map(n => String(n).padStart(2, '0')).join(', ');
          
          replyText = `🎯 あなたの今日のラッキー予想\n【 ${sorted} 】\n\nAI最新予想はサイトで公開中！\nhttps://loto-yosou-ai.com/\n\n💰購入代行はこちら👇\n${process.env.AFFILIATE_BUY_SERVICE || 'https://loto-yosou-ai.com/'}`;
        
        } else if (userText === 'おみくじ') {
          const fortunes = ['【大吉】金運爆発！高額当選の予感💰', '【中吉】堅実に行こう！手堅く当たるかも✨', '【小吉】少額で運試しが吉🍀'];
          const result = fortunes[Math.floor(Math.random() * fortunes.length)];
          replyText = `${result}\n\n✨運気をさらに上げる開運アイテム👇\n${process.env.AFFILIATE_LUCKY_ITEM || 'https://loto-yosou-ai.com/'}`;
        
        } else {
          replyText = 'メニューのボタンを押すか、「ロト6」や「おみくじ」とメッセージを送ってみてね！';
        }
        // ▲▲▲ ここまで ▲▲▲

        // LINEユーザーへ返信
        await client.replyMessage({
          replyToken: event.replyToken,
          messages: [{ type: 'text', text: replyText }],
        });
      }
    }

    // Vercel(LINE)に成功を伝える
    return res.status(200).json({ status: 'success' });

  } catch (error) {
    console.error(error);
    return res.status(500).json({ status: 'error' });
  }
}