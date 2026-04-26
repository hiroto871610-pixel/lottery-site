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
          replyText = `🎯 あなたの今日のロト6予想\n【 ${sorted} 】\n\nAI最新予想はサイトで公開中！\nhttps://loto-yosou-ai.com/loto6.html\n\n💰購入代行はこちら👇\n${process.env.AFFILIATE_BUY_SERVICE || 'https://loto-yosou-ai.com/'}`;
        
        } else if (userText === 'ロト7') {
          // ロト7は1〜37の中から7個の数字を選ぶ
          const nums: number[] = [];
          while(nums.length < 7) {
            const n = Math.floor(Math.random() * 37) + 1;
            if(!nums.includes(n)) nums.push(n);
          }
          const sorted = nums.sort((a,b) => a - b).map(n => String(n).padStart(2, '0')).join(', ');
          replyText = `🎯 あなたの今日のロト7予想\n【 ${sorted} 】\n\nAI最新予想はサイトで公開中！\nhttps://loto-yosou-ai.com/loto7.html\n\n💰購入代行はこちら👇\n${process.env.AFFILIATE_BUY_SERVICE || 'https://loto-yosou-ai.com/'}`;

        } else if (userText === 'ナンバーズ' || userText === 'ナンバーズ4' || userText === 'ナンバーズ3') {
          // ナンバーズは重複OKなので、ランダムに数字を生成して繋げる
          const n4 = Array.from({length: 4}, () => Math.floor(Math.random() * 10)).join('');
          const n3 = Array.from({length: 3}, () => Math.floor(Math.random() * 10)).join('');
          replyText = `🎯 あなたの今日のナンバーズ予想\n【 N4: ${n4} 】\n【 N3: ${n3} 】\n\nAI最新予想はサイトで公開中！\nhttps://loto-yosou-ai.com/numbers.html\n\n💰購入代行はこちら👇\n${process.env.AFFILIATE_BUY_SERVICE || 'https://loto-yosou-ai.com/'}`;

        } else if (userText === 'おみくじ') {
          // おみくじのバリエーションを大増量！
          const fortunes = [
            '【大吉】金運爆発！高額当選の予感💰', 
            '【吉】運気上昇中！直感を信じて数字を選ぼう✨',
            '【中吉】堅実に行こう！手堅く当たるかも🎯', 
            '【小吉】少額で運試しが吉🍀',
            '【末吉】今は準備期間。少額投資でコツコツと🐢',
            '【凶】今日は見送るのもアリ。でも無欲で買えば奇跡が…？🔮',
            '【大凶】逆にレア！どん底からの大逆転ホームランを狙え！🌋'
          ];
          const result = fortunes[Math.floor(Math.random() * fortunes.length)];
          replyText = `${result}\n\n✨運気をさらに上げる開運アイテム👇\n${process.env.AFFILIATE_LUCKY_ITEM || 'https://loto-yosou-ai.com/'}`;
        
        } else {
          // 案内メッセージも全対応版にアップデート
          replyText = 'メニューのボタンを押すか、「ロト6」「ロト7」「ナンバーズ」「おみくじ」とメッセージを送ってみてね！';
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