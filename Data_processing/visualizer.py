import datetime as dt
import matplotlib; matplotlib.use('agg')
import matplotlib.pyplot as plt
import numpy as np
import cv2

class Live_plotting:

    def __init__(self):
        self.fig, self.axs = plt.subplots(3, sharex=True, figsize=(5.12, 5.12))
        self.num_time = []

        self.mag_data = {'x': [], 'y': [], 'z': []}
        self.mag_color = {'x': 'blue', 'y': 'red', 'z': 'green'}

        self.temp_data = {'in': [], 'out': []}
        self.temp_color = {'in': 'blue', 'out': 'red'}

        self.pres_data = []

    def plotting(self, mag, temp, pres, img, is_aurora):
        self.num_time.append(dt.datetime.now().strftime('%H:%M:%S'))
        self.num_time = self.num_time[-20:]

        self.axs[0].clear()
        for key, val in self.mag_data.items():
            self.mag_data[key].append(mag[key])
            self.mag_data[key] = self.mag_data[key][-20:]
            self.axs[0].plot(self.num_time, self.mag_data[key], color=self.mag_color[key], label=key)
        self.axs[0].set_title("Magnetic Fields")
        self.axs[0].set_ylabel("nT")
        self.axs[0].legend(loc="upper right")

        self.axs[1].clear()
        for key, val in self.temp_data.items():
            self.temp_data[key].append(temp[key])
            self.temp_data[key] = self.temp_data[key][-20:]
            self.axs[1].plot(self.num_time, self.temp_data[key], color=self.temp_color[key], label=key)
        self.axs[1].set_title("Temperature")
        self.axs[1].set_ylabel("°C")
        self.axs[1].legend(loc="upper right")

        self.axs[2].clear()
        self.pres_data.append(pres)
        self.pres_data = self.pres_data[-20:]
        self.axs[2].plot(self.num_time, self.pres_data, color='blue')
        self.axs[2].set_title("Pressure")
        self.axs[2].set_ylabel("hPa")

        plt.setp(self.axs[2].get_xticklabels(), rotation=45, ha="right")
        self.fig.tight_layout()
        
        # img = np.zeros((512, 512, 3), dtype=np.uint8)

        self.fig.canvas.draw()
        plot = np.fromstring(self.fig.canvas.tostring_argb(), dtype=np.uint8,  # Changed to argb
                             sep='')
        plot = plot.reshape(self.fig.canvas.get_width_height()[::-1] + (4,))   # from 3 ---> 4 not sure why
        plot = cv2.cvtColor(plot, cv2.COLOR_RGB2BGR)
        # print(plot.dtype, img.dtype)
        plot = np.hstack([cv2.putText(img, str(is_aurora), (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (225, 225, 225), 2), plot])

        cv2.imshow("data", plot)
        cv2.waitKey(1)
