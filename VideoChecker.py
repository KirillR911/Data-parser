import shutil

from tqdm import tqdm

from ffe import *


# __init__ get a path to directory to examine

# TODO here we can also save detected faces

class VideoChecker(object):
    def __init__(self, directory):
        self.directory = directory

    def check(self, fa, device=None, model=None, debug=False, ):
        '''
            Предполагаем, что на первом кадре всегда искомый спикер
            Берём его лицо как таргет
            Просматриваем все последующие кадры и ищем на них таргет спикера
            При этом в cur_v записывается найденное лицо в виде класса FFE.Face или None, если нет лица
            ближе чем ∆
        '''
        device = torch.device(
            'cuda:0' if torch.cuda.is_available() else 'cpu') if device is None else device
        for file in (os.listdir(self.directory)):

            print('=' * 20, f"processing {file}", "=" * 20)
            if ".DS_Store" in file or ".mp4" not in file:
                continue
            f_dir = self.directory + "/" + file[:-4] + "/"
            if os.path.exists(f_dir):
                print("file already checked!")
                continue
            if not os.path.exists(self.directory + "/" + file[:-4] + "/"):
                os.mkdir(self.directory + "/" + file[:-4] + "/")

            correctFile = True
            cap = cv2.VideoCapture(self.directory + "/" + file)
            ret, frame = cap.read()
            if not ret:
                print("BROKEN VIDEO not ret")
                os.remove(self.directory + "/" + file)
                shutil.rmtree(f_dir)
                continue
            try:
                im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                im_p = ParsableImage(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), device=device, name=file, face_al=fa)
                im_p.parseFaces(margin=60, model=model)
            except Exception as ex:
                print("BROKEN VIDEO cant read imge ", ex)
                os.remove(self.directory + "/" + file)
                shutil.rmtree(f_dir)
                continue

            if im_p.faces is None or len(im_p.faces) == 0:
                print(f"[ERROR] Can't find faces on image !")
                os.remove(self.directory + "/" + file)
                shutil.rmtree(f_dir)
                continue
            else:
                prev_v = im_p.faces[0].getVector()

            im_p.faces[0].faceImage.save(self.directory + "/" + file[:-4] + "/" + str(0) + ".jpg")
            im_p.showBoxes()
            im_p.parsedImage.save(f"./{file}_Debug.jpg")
            np.save(self.directory + "/" + file[:-4] + "/2D" + str(0), im_p.faces[0].lms2d)
            np.save(self.directory + "/" + file[:-4] + "/3D" + str(0), im_p.faces[0].lms3d)
            idx = 1
            length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            pbar = tqdm(total=length + 1)
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    print("BROKEN VIDEO not ret")
                    break
                try:
                    im_p = ParsableImage(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), device, file, face_al=fa)
                    im_p.parseFaces(margin=60, model=model)
                except Exception as ex:
                    print(f"[ERROR] Can't find faces on image  Cant Parse cause of {ex}")
                    im_p.PILImage.save(f"{file}WHAT?.jpg")
                    correctFile = False
                    break

                if len(im_p.faces) == 0:
                    print(f"[ERROR] Can't find faces on image ! No faces")
                    correctFile = False
                    break
                cur_v = find_face_on_image(im_p.faces, prev_v, im_p.PILImage, file)

                if cur_v is None:
                    print(f"[ERROR] Can't find speaker face on image ! Speaker not found")
                    correctFile = False
                    break

                cur_v.faceImage.save(self.directory + "/" + file[:-4] + "/" + str(idx) + ".jpg")
                im_p.showBoxes()
                im_p.parsedImage.save(f"./{file}_sample.jpg")
                np.save(self.directory + "/" + file[:-4] + "/2D" + str(idx), cur_v.lms2d)
                np.save(self.directory + "/" + file[:-4] + "/3D" + str(idx), cur_v.lms3d)
                if debug:
                    tmp = cur_v.faceImage.copy()
                    imageD = ImageDraw.Draw(tmp)
                    for (x, y) in cur_v.dlibs_m:
                        # print(x, y)
                        imageD.point((x, y), 'green')
                    tmp.save("DEBUG" + file.rstrip(".mp4") + ".jpg")
                idx += 1
                im_p.flush()
                del cur_v
                # dump_tensors()
                pbar.update(1)

            pbar.close()
            print("CORRECT?", correctFile)
            print("FNAME", file)
            cap.release()
            del prev_v
            if not correctFile:
                os.remove(self.directory + "/" + file)
                shutil.rmtree(f_dir)
