import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Send } from "lucide-react";
import { api } from "../api/client";

export function ReportPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const body = Object.fromEntries(form.entries());
    const numeric = ["latitude", "longitude", "number_of_people", "number_of_children", "number_of_elderly", "number_of_injured", "water_level"];
    numeric.forEach((key) => {
      if (body[key] === "") delete body[key];
      else if (body[key] !== undefined) body[key] = Number(body[key]) as never;
    });
    body.has_disabled_person = form.has("has_disabled_person") as never;
    body.has_pregnant_person = form.has("has_pregnant_person") as never;
    body.is_trapped = form.has("is_trapped") as never;
    try {
      const created = await api.createRequest(body);
      navigate("/report/success", { state: created });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không gửi được yêu cầu");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto max-w-3xl">
      <div className="mb-5">
        <h1 className="text-2xl font-bold">Gửi yêu cầu cứu hộ</h1>
        <p className="text-sm text-slate-600">Nhập được thông tin nào thì gửi thông tin đó. Hệ thống sẽ tiếp nhận và chuyển về Ban Chỉ huy.</p>
      </div>
      <form onSubmit={submit} className="grid gap-4 rounded border border-slate-200 bg-white p-4">
        <div className="grid gap-4 md:grid-cols-2">
          <label><span className="label">Họ tên</span><input name="reporter_name" className="field" /></label>
          <label><span className="label">Số điện thoại</span><input name="phone_number" className="field" /></label>
        </div>
        <label><span className="label">Nội dung cầu cứu</span><textarea required name="message" className="field min-h-28" placeholder="Ví dụ: Nhà tôi có 5 người, nước đang lên rất nhanh..." /></label>
        <label><span className="label">Địa chỉ hoặc mô tả vị trí</span><input name="address" className="field" /></label>
        <div className="grid gap-4 md:grid-cols-2">
          <label><span className="label">Latitude</span><input name="latitude" type="number" step="any" className="field" /></label>
          <label><span className="label">Longitude</span><input name="longitude" type="number" step="any" className="field" /></label>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          <label><span className="label">Số người</span><input name="number_of_people" type="number" min="0" defaultValue="1" className="field" /></label>
          <label><span className="label">Trẻ em</span><input name="number_of_children" type="number" min="0" defaultValue="0" className="field" /></label>
          <label><span className="label">Người cao tuổi</span><input name="number_of_elderly" type="number" min="0" defaultValue="0" className="field" /></label>
          <label><span className="label">Bị thương</span><input name="number_of_injured" type="number" min="0" defaultValue="0" className="field" /></label>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <label><span className="label">Mực nước ước tính mét</span><input name="water_level" type="number" min="0" step="0.1" className="field" /></label>
          <label><span className="label">Ghi chú bổ sung</span><input name="note" className="field" /></label>
        </div>
        <div className="flex flex-wrap gap-4 text-sm">
          <label className="inline-flex items-center gap-2"><input type="checkbox" name="is_trapped" /> Đang mắc kẹt</label>
          <label className="inline-flex items-center gap-2"><input type="checkbox" name="has_disabled_person" /> Có người khuyết tật</label>
          <label className="inline-flex items-center gap-2"><input type="checkbox" name="has_pregnant_person" /> Có phụ nữ mang thai</label>
        </div>
        {error && <div className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <button disabled={loading} className="inline-flex w-fit items-center gap-2 rounded bg-critical px-4 py-2 font-semibold text-white disabled:opacity-60">
          <Send size={18} /> {loading ? "Đang gửi" : "Gửi SOS"}
        </button>
      </form>
    </section>
  );
}
