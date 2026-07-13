import { Link, useLocation } from "react-router-dom";
import { RescueRequest } from "../api/client";

export function SuccessPage() {
  const { state } = useLocation();
  const request = state as RescueRequest | undefined;
  return (
    <section className="mx-auto max-w-xl rounded border border-slate-200 bg-white p-6">
      <h1 className="mb-3 text-2xl font-bold">Yêu cầu của bạn đã được tiếp nhận.</h1>
      {request ? (
        <div className="space-y-2 text-slate-800">
          <p>Mã yêu cầu: <strong>{request.request_code}</strong></p>
          <p>Trạng thái: <strong>{request.status}</strong></p>
          <p>Thời gian gửi: {new Date(request.created_at).toLocaleString("vi-VN")}</p>
          <p className="pt-2 text-sm text-slate-600">Hãy giữ điện thoại trong trạng thái có thể liên lạc.</p>
        </div>
      ) : (
        <p>Không tìm thấy thông tin yêu cầu vừa gửi.</p>
      )}
      <Link to="/report" className="mt-5 inline-block rounded bg-command px-4 py-2 text-white">Gửi yêu cầu khác</Link>
    </section>
  );
}
