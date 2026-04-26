import { NextRequest, NextResponse } from 'next/server';
import * as line from '@line/bot-sdk';

// LINEの認証情報を環境変数から取得
const config = {
  channelAccessToken: process.env.LINE_CHANNEL_ACCESS_TOKEN || '',
  channelSecret: process.env.LINE_CHANNEL_SECRET || '',
};

// Messaging APIクライアントの初期化
const client = new line.messagingApi.MessagingApiClient({
  channelAccessToken: config.channelAccessToken,
});

export async function POST(req: NextRequest) {
  try {
    const body = await req.text();
    const signature = req.headers.get('x-line-signature');

    // 1. 署名の検証（本当にLINEからのリクエストか確認）
    if (!signature || !line.validateSignature(body, config.channelSecret, signature)) {
      return NextResponse.json({ error: 'Invalid signature' }, { status: 401 });
    }

    const events = JSON.parse(body).events;

    // 2. 受け取ったイベントを処理
    for (const event of events) {
      // テキストメッセージが送られてきた場合のみ反応する
      if (event.type === 'message' && event.message.type === 'text') {
        const userText = event.message.text;
        let replyText = '';

        // ▼▼▼ ここが「自動応答・おみくじ」のロジックです ▼▼▼
        if (userText === 'ロト6') {
          // ランダムな6つの数字を生成（簡易予想）
          const nums: number[] = [];
          while(nums.length < 6) {
            const n = Math.floor(Math.random() * 43) + 1;
            if(!nums.includes(n)) nums.push(n);
          }
          const sorted = nums.sort((a,b) => a - b).map(n => String(n).padStart(2, '0')).join(', ');
          
          replyText = `🎯 あなたの今日のラッキー予想\n【 ${sorted} 】\n\nAIによる超本気の最新予想はサイトで公開中！\nhttps://loto-yosou-ai.com/\n\n💰購入代行はこちら👇\n${process.env.AFFILIATE_BUY_SERVICE || 'https://px.a8.net/...'}`;
        
        } else if (userText === 'おみくじ') {
          // おみくじロジック
          const fortunes = [
            '【大吉】金運爆発！高額当選の予感💰', 
            '【中吉】堅実に行こう！手堅く当たるかも✨', 
            '【小吉】少額で運試しが吉🍀'
          ];
          const result = fortunes[Math.floor(Math.random() * fortunes.length)];
          
          replyText = `${result}\n\n✨運気をさらに上げる開運アイテム👇\n${process.env.AFFILIATE_LUCKY_ITEM || 'https://px.a8.net/...'}`;
        
        } else {
          // それ以外の言葉には使い方を案内
          replyText = 'メニューのボタンを押すか、「ロト6」や「おみくじ」とメッセージを送ってみてね！';
        }
        // ▲▲▲ ここまで ▲▲▲

        // 3. ユーザーへ返信を実行
        if (replyText) {
          await client.replyMessage({
            replyToken: event.replyToken,
            messages: [{ type: 'text', text: replyText }],
          });
        }
      }
    }

    // LINEサーバーに「無事受け取りました」と200を返す
    return NextResponse.json({ status: 'success' }, { status: 200 });

  } catch (error) {
    console.error('Webhook Error:', error);
    return NextResponse.json({ status: 'error' }, { status: 500 });
  }
}