import { useState } from "react";
import { toast } from "react-toastify";
import Toast from "../components/Toast";
import Button from "../components/Button";
import Input from "../components/Input";
import "react-toastify/dist/ReactToastify.css";

export default function HRProfile() {
  const initialProfile = {
    fullName: "Ramisetty Purneswari",
    email: "purneswari@gmail.com",
    department: "Human Resources",
    joinedDate: "2024-01-15",
    interviewsConducted: 128,
  };

  const [profile, setProfile] = useState(initialProfile);
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setProfile({
      ...profile,
      [e.target.name]: e.target.value,
    });
  };

  const hasChanges =
    JSON.stringify(profile) !== JSON.stringify(initialProfile);

  const saveProfile = async () => {
    if (!hasChanges) {
      toast.info("No changes detected");
      return;
    }

    setLoading(true);

    try {
      console.log("Saving Profile...");
      console.log(profile);

      await new Promise((resolve) => setTimeout(resolve, 1500));

      const success = Math.random() > 0.2;

      if (success) {
        toast.success("Profile updated successfully");
      } else {
        throw new Error();
      }
    } catch {
      toast.error("Failed to save profile");
    }

    setLoading(false);
  };

  const changePassword = () => {
    toast.info("Password change feature coming soon.");
  };

  return (
    <>
      <Toast />

      <div className="container">

        <div className="card">

          <h1>HR Profile</h1>

          <div className="form-group">
            <label>Full Name</label>

            <Input
                label="Full Name"
                name="fullName"
                value={profile.fullName}
                onChange={handleChange}
            />
          </div>

          <div className="form-group">
            <label>Email</label>

            <Input
                label="Email"
                value={profile.email}
                disabled
            />
          </div>

          <div className="form-group">
            <label>Department</label>

            <Input
                label="Department"
                name="department"
                value={profile.department}
                onChange={handleChange}
            />
          </div>

          <div className="form-group">
            <label>Joined Date</label>

            <Input
                label="Joined Date"
                type="date"
                name="joinedDate"
                value={profile.joinedDate}
                onChange={handleChange}
            />
          </div>

          <div className="form-group">
            <label>Interviews Conducted</label>

            <Input
                label="Interviews Conducted"
                value={profile.interviewsConducted}
                disabled
            />
          </div>

          <div className="button-group">

            <Button
            className="save-btn"
            disabled={loading}
            onClick={saveProfile}
            >
            {loading ? "Saving..." : "Save Changes"}
            </Button>

            <Button
            className="password-btn"
            onClick={changePassword}
            >
            Change Password
            </Button>

            </div>

        </div>

      </div>
    </>
  );
}